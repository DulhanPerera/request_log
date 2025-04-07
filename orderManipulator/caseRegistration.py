import json
from datetime import datetime, date
from decimal import Decimal
import requests
import pymysql
from pymongo import MongoClient
from utils.database.connectSQL import get_mysql_connection
from utils.logger.logger import get_logger
from utils.api.connectAPI import read_api_config
from utils.custom_exceptions.customize_exceptions import APIConfigError, IncidentCreationError

logger = get_logger("task_status_logger")
if len(logger.handlers) > 1:  # Remove duplicates
    logger.handlers = [logger.handlers[0]]  # Keep first handler
logger.propagate = False  # Stop propagation

class IncidentProcessor:
    
    def __init__(self, account_num, incident_id, mongo_collection):
        self.account_num = str(account_num)
        self.incident_id = int(incident_id)
        self.collection = mongo_collection
        self.mongo_data = self.initialize_mongo_doc()

    def initialize_mongo_doc(self):
        now = datetime.now().replace(microsecond=0).isoformat() + ".000Z"
        return {
            "Doc_Version": 1,
            "Incident_Id": self.incident_id,
            "Account_Num": self.account_num,
            "Arrears": 0,
            "arrears_band": "",
            "Created_By": "drs_admin",
            "Created_Dtm": now,
            "Incident_Status": "",
            "Incident_Status_Dtm": now,
            "Status_Description": "",
            "File_Name_Dump": "",
            "Batch_Id": "",
            "Batch_Id_Tag_Dtm": now,
            "External_Data_Update_On": now,
            "Filtered_Reason": "",
            "Export_On": now,
            "File_Name_Rejected": "",
            "Rejected_Reason": "",
            "Incident_Forwarded_By": "",
            "Incident_Forwarded_On": now,
            "Contact_Details": [],
            "Product_Details": [],
            "Customer_Details": {},
            "Account_Details": {},
            "Last_Actions": [],
            "Marketing_Details": [{
                "ACCOUNT_MANAGER": "",
                "CONSUMER_MARKET": "",
                "Informed_To": "",
                "Informed_On": "1900-01-01T00:00:00.100Z"
            }],
            "Action": "",
            "Validity_period": "0",
            "Remark": "",
            "updatedAt": now,
            "Rejected_By": "",
            "Rejected_Dtm": now,
            "Arrears_Band": "",
            "Source_Type": ""
        }

    def read_customer_details(self):
        """Retrieves and processes customer account data from MySQL"""
        mysql_conn = None
        cursor = None
        try:
            logger.info(f"Reading customer details for account number: {self.account_num}")
            mysql_conn = get_mysql_connection()
            if not mysql_conn:
                logger.error("MySQL connection failed. Skipping customer details retrieval.")
                return "error"
            
            cursor = mysql_conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(f"SELECT * FROM debt_cust_detail WHERE ACCOUNT_NUM = '{self.account_num}'")
            rows = cursor.fetchall()

            seen_products = set()
            seen_contacts = set()

            for row in rows:
                # Normalize date for Contact_Details
                load_date = row.get("LOAD_DATE")
                if load_date:
                    if isinstance(load_date, str):  # Handle string input
                        load_date = datetime.strptime(load_date, "%Y-%m-%d %H:%M:%S")
                    elif isinstance(load_date, date) and not isinstance(load_date, datetime):  # Handle date-only
                        load_date = datetime.combine(load_date, datetime.min.time())
                    load_date_str = load_date.replace(microsecond=0).isoformat() + ".000Z"
                else:
                    load_date_str = "1900-01-01T00:00:00.000Z"

                if row.get("TECNICAL_CONTACT_EMAIL"):
                    email = row["TECNICAL_CONTACT_EMAIL"] if "@" in row["TECNICAL_CONTACT_EMAIL"] else ""
                    contact_key = ("email", email)
                    if contact_key not in seen_contacts:
                        seen_contacts.add(contact_key)
                        self.mongo_data["Contact_Details"].append({
                            "Contact_Type": "email",
                            "Contact": email,
                            "Create_Dtm": load_date_str,
                            "Create_By": "drs_admin"
                        })

                if row.get("MOBILE_CONTACT"):
                    mobile = row["MOBILE_CONTACT"]
                    contact_key = ("mobile", mobile)
                    if contact_key not in seen_contacts:
                        seen_contacts.add(contact_key)
                        self.mongo_data["Contact_Details"].append({
                            "Contact_Type": "mobile",
                            "Contact": mobile,
                            "Create_Dtm": load_date_str,
                            "Create_By": "drs_admin"
                        })

                if row.get("WORK_CONTACT"):
                    work = row["WORK_CONTACT"]
                    contact_key = ("fix", work)
                    if contact_key not in seen_contacts:
                        seen_contacts.add(contact_key)
                        self.mongo_data["Contact_Details"].append({
                            "Contact_Type": "fix",
                            "Contact": work,
                            "Create_Dtm": load_date_str,
                            "Create_By": "drs_admin"
                        })

                # Customer_Details
                if not self.mongo_data["Customer_Details"]:
                    self.mongo_data["Customer_Details"] = {
                        "Customer_Name": row.get("CONTACT_PERSON", ""),
                        "Company_Name": "",
                        "Company_Registry_Number": "",
                        "Full_Address": row.get("ASSET_ADDRESS", ""),
                        "Zip_Code": row.get("ZIP_CODE", ""),
                        "Customer_Type_Name": "",
                        "Nic": str(row.get("NIC", "")),
                        "Customer_Type_Id": int(row.get("CUSTOMER_TYPE_ID", 0)),
                        "Customer_Type": row.get("CUSTOMER_TYPE", "")
                    }

                    # Account_Details with normalized date
                    acc_eff_dtm = row.get("ACCOUNT_EFFECTIVE_DTM_BSS")
                    if acc_eff_dtm:
                        if isinstance(acc_eff_dtm, str):
                            acc_eff_dtm = datetime.strptime(acc_eff_dtm, "%Y-%m-%d %H:%M:%S")
                        elif isinstance(acc_eff_dtm, date) and not isinstance(acc_eff_dtm, datetime):
                            acc_eff_dtm = datetime.combine(acc_eff_dtm, datetime.min.time())
                        acc_eff_dtm_str = acc_eff_dtm.replace(microsecond=0).isoformat() + ".000Z"
                    else:
                        acc_eff_dtm_str = "1900-01-01T00:00:00.000Z"

                    self.mongo_data["Account_Details"] = {
                        "Account_Status": row.get("ACCOUNT_STATUS_BSS", ""),
                        "Acc_Effective_Dtm": acc_eff_dtm_str,
                        "Acc_Activate_Date": "1900-01-01T00:00:00.000Z",
                        "Credit_Class_Id": int(row.get("CREDIT_CLASS_ID", 0)),
                        "Credit_Class_Name": row.get("CREDIT_CLASS_NAME", ""),
                        "Billing_Centre": row.get("BILLING_CENTER_NAME", ""),
                        "Customer_Segment": row.get("CUSTOMER_SEGMENT_ID", ""),
                        "Mobile_Contact_Tel": "",
                        "Daytime_Contact_Tel": "",
                        "Email_Address": str(row.get("EMAIL", "")),
                        "Last_Rated_Dtm": "1900-01-01T00:00:00.000Z"
                    }

                # Product_Details with normalized date
                eff_dtm = row.get("ACCOUNT_EFFECTIVE_DTM_BSS")
                if eff_dtm:
                    if isinstance(eff_dtm, str):
                        eff_dtm = datetime.strptime(eff_dtm, "%Y-%m-%d %H:%M:%S")
                    elif isinstance(eff_dtm, date) and not isinstance(eff_dtm, datetime):
                        eff_dtm = datetime.combine(eff_dtm, datetime.min.time())
                    eff_dtm_str = eff_dtm.replace(microsecond=0).isoformat() + ".000Z"
                else:
                    eff_dtm_str = "1900-01-01T00:00:00.000Z"

                product_id = row.get("ASSET_ID")
                if product_id and product_id not in seen_products:
                    seen_products.add(product_id)
                    self.mongo_data["Product_Details"].append({
                        "Product_Label": row.get("PROMOTION_INTEG_ID", ""),
                        "Customer_Ref": row.get("CUSTOMER_REF", ""),
                        "Product_Seq": int(row.get("BSS_PRODUCT_SEQ", 0)),
                        "Equipment_Ownership": "",
                        "Product_Id": product_id,
                        "Product_Name": row.get("PRODUCT_NAME", ""),
                        "Product_Status": row.get("ASSET_STATUS", ""),
                        "Effective_Dtm": eff_dtm_str,
                        "Service_Address": row.get("ASSET_ADDRESS", ""),
                        "Cat": row.get("CUSTOMER_TYPE_CAT", ""),
                        "Db_Cpe_Status": "",
                        "Received_List_Cpe_Status": "",
                        "Service_Type": row.get("OSS_SERVICE_ABBREVIATION", ""),
                        "Region": row.get("CITY", ""),
                        "Province": row.get("PROVINCE", "")
                    })

            logger.info("Successfully read customer details.")
            return "success"

        except Exception as e:
            logger.error(f"Error : {e}")
            return "error"
        finally:
            if cursor:
                cursor.close()
            if mysql_conn:
                mysql_conn.close()

    def get_payment_data(self):
        """Retrieves and processes the most recent payment record for the account from MySQL."""
        mysql_conn = None
        cursor = None
        try:
            logger.info(f"Getting payment data for account number: {self.account_num}")
            mysql_conn = get_mysql_connection()
            if not mysql_conn:
                logger.error("MySQL connection failed. Skipping payment data retrieval.")
                return "failure"
            
            cursor = mysql_conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                f"SELECT * FROM debt_payment WHERE AP_ACCOUNT_NUMBER = '{self.account_num}' "
                "ORDER BY ACCOUNT_PAYMENT_DAT DESC LIMIT 1"
            )
            payment_rows = cursor.fetchall()

            if payment_rows:
                payment = payment_rows[0]
                payment_date = payment.get("ACCOUNT_PAYMENT_DAT")
                if payment_date:
                    if isinstance(payment_date, str):
                        payment_date = datetime.strptime(payment_date, "%Y-%m-%d %H:%M:%S")
                    elif isinstance(payment_date, date) and not isinstance(payment_date, datetime):
                        payment_date = datetime.combine(payment_date, datetime.min.time())
                    payment_date_str = payment_date.replace(microsecond=0).isoformat() + ".000Z"
                else:
                    payment_date_str = "1900-01-01T00:00:00.000Z"

                self.mongo_data["Last_Actions"].append({
                    "Billed_Seq": int(payment.get("ACCOUNT_PAYMENT_SEQ", 0)),
                    "Billed_Created": payment_date_str,
                    "Payment_Seq": int(payment.get("ACCOUNT_PAYMENT_SEQ", 0)),
                    "Payment_Created": payment_date_str,
                    "Payment_Money": float(payment.get("AP_ACCOUNT_PAYMENT_MNY", 0)),
                    "Billed_Amount": float(payment.get("AP_ACCOUNT_PAYMENT_MNY", 0))
                })
                logger.info("Successfully retrieved payment data.")
                return "success"
            return "failure"

        except Exception as e:
            logger.error(f"Error : {e}")
            return "failure"
        finally:
            if cursor:
                cursor.close()
            if mysql_conn:
                mysql_conn.close()

    def format_json_object(self):
        json_data = json.loads(json.dumps(self.mongo_data, default=self.json_serializer()))
        json_data["Customer_Details"]["Nic"] = str(json_data["Customer_Details"].get("Nic", ""))
        json_data["Account_Details"]["Email_Address"] = str(json_data["Account_Details"].get("Email_Address", ""))
        return json.dumps(json_data, indent=4)

    def json_serializer(self):
        def _serialize(obj):
            if isinstance(obj, (datetime, date)):
                if isinstance(obj, date) and not isinstance(obj, datetime):
                    obj = datetime.combine(obj, datetime.min.time())
                return obj.replace(microsecond=0).isoformat() + ".000Z"
            if isinstance(obj, Decimal):
                return float(obj)
            if obj is None:
                return ""
            raise TypeError(f"Type {type(obj)} not serializable")
        return _serialize

    def send_to_api(self, json_output, api_url):
        logger.info(f"Sending data to API: {api_url}")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        try:
            response = requests.post(api_url, data=json_output, headers=headers)
            response.raise_for_status()
            logger.info("Successfully sent data to API.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending data to API: {e}")
            return None

    def process_incident(self):
        try:
            logger.info(f"Processing incident for account: {self.account_num}, ID: {self.incident_id}")
            
            customer_status = self.read_customer_details()
            if customer_status != "success" or not self.mongo_data["Customer_Details"]:
                error_msg = f"No customer details found for account {self.account_num}"
                logger.error(error_msg)
                return False, error_msg
            
            payment_status = self.get_payment_data()
            if payment_status != "success":
                logger.warning(f"Failed to retrieve payment data for account {self.account_num}")
                
            json_output = self.format_json_object()
            print(json_output)
            
            api_url = read_api_config()
            if not api_url:
                raise APIConfigError("Empty API URL in config")
                    
            api_response = self.send_to_api(json_output, api_url)
            if not api_response:
                raise IncidentCreationError("Empty API response")
                    
            logger.info(f"API Success: {api_response}")
            return True, api_response
                
        except IncidentCreationError as e:
            logger.error(f"Incident processing failed: {e}")
            return False, str(e)
        except APIConfigError as e:
            logger.error(f"Configuration error: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return False, str(e)