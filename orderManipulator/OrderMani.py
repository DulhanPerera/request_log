import time
from utils.database.connectMongoDB import get_mongo_collection
from utils.logger.logger import get_logger

logger = get_logger("OrderProcessor")

class OrderProcessor:
    def __init__(self):
        # Initialize MongoDB connection
        self.collection = get_mongo_collection()
        if self.collection is None:
            raise ConnectionError("Failed to connect to MongoDB collection")
        
        logger.info("MongoDB connection established successfully")

    def process_case(self, account_number, incident_id):
        """Process customer details for case registration"""
        logger.info(f"Processing Case Registration for account: {account_number}, incident: {incident_id}")
        # Add your actual processing logic here

    def get_open_orders(self):
        """Fetch all documents with request_status: 'Open'"""
        try:
            return list(self.collection.find({"request_status": "Open"}))
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []

    def process_option_1(self, documents):
        """Process documents for option 1 using match-case"""
        processed_count = 0
        for doc in documents:
            match doc.get('order_id'):
                case 1:
                    try:
                        account_number = doc.get('account_number')
                        incident_id = doc.get('parameters', {}).get('incident_id')
                        
                        if account_number and incident_id:
                            self.process_case(account_number, incident_id)
                            processed_count += 1
                        else:
                            logger.warning(f"Missing required fields in document: {doc.get('_id')}")
                    except Exception as e:
                        logger.error(f"Error processing document {doc.get('_id')}: {str(e)}")
                case _:
                    continue  # Skip documents with other order_ids
        logger.info(f"Processed {processed_count} documents for option 1")

    def show_menu(self):
        """Display the user menu"""
        print("\nSelect an option:")
        print("1: Cust Details for Case Registration")
        print("2: Monitor Payment")
        print("3: Monitor Payment Cancel")
        print("4: Close_Monitor_If_No_Transaction")
        try:
            return int(input("Enter option (1-4): "))
        except ValueError:
            logger.warning("Invalid menu input - expected number 1-4")
            return None

    def process_selected_option(self, option, documents):
        """Handle the selected option"""
        match option:
            case 1:
                self.process_option_1(documents)
            case 2:
                logger.info("Option 2 selected - Monitor Payment")
                # self.process_option_2(documents)
            case 3:
                logger.info("Option 3 selected - Monitor Payment Cancel")
                # self.process_option_3(documents)
            case 4:
                logger.info("Option 4 selected - Close_Monitor_If_No_Transaction")
                # self.process_option_4(documents)
            case _:
                logger.warning(f"Invalid option selected: {option}")

    def run(self):
        """Main processing loop"""
        logger.info("Starting Order Processor")
        while True:
            try:
                # Get open orders
                open_orders = self.get_open_orders()
                
                if not open_orders:
                    logger.info("No open orders found. Waiting...")
                    time.sleep(5)
                    continue
                    
                logger.info(f"Found {len(open_orders)} open orders")
                
                # Get user input
                option = self.show_menu()
                if option is None:
                    print("Invalid input. Please enter a number between 1-4.")
                    continue
                
                # Process selected option
                self.process_selected_option(option, open_orders)
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Program terminated by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                time.sleep(5)

if __name__ == "__main__":
    try:
        processor = OrderProcessor()
        processor.run()
    except Exception as e:
        logger.critical(f"Failed to start OrderProcessor: {e}")