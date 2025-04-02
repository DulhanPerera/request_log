import time
from utils.database.connectMongoDB import get_mongo_collection
from .caseRegistration import IncidentProcessor
from utils.logger.logger import get_logger

logger = get_logger("OrderProcessor")

class OrderProcessor:
    def __init__(self):
        self.collection = get_mongo_collection()
        if self.collection is None:
            raise ConnectionError("Failed to connect to MongoDB collection")
        logger.info("MongoDB connection established successfully")

    def process_case(self, account_number, incident_id):
        """
        Process customer details for case registration
        """
        logger.info(f"Processing case for account: {account_number}, incident: {incident_id}")
        
        # Create and process incident
        processor = IncidentProcessor(
            account_num=account_number,
            incident_id=incident_id,
            mongo_collection=self.collection
        )
        
        return processor.process_incident()

    def get_open_orders(self):
        """Get all open orders including _id for logging purposes"""
        return list(self.collection.find({"request_status": "Open"}))

    def process_option_1(self, documents):
        """
        Process documents for option 1 while ignoring _id field
        Args:
            documents: List of MongoDB documents (may contain _id)
        Returns:
            Tuple: (processed_count, error_count)
        """
        processed_count = 0
        error_count = 0
        
        for doc in documents:
            try:
                # Retain _id for logging purposes
                doc_id = doc.get('_id', 'NO_ID')
                
                # Create a clean copy without _id for processing
                doc_data = {k: v for k, v in doc.items() if k != '_id'}
                
                # Skip if not the right order_id
                if doc_data.get('order_id') != 1:
                    continue
                    
                # Extract required fields
                account_number = doc_data.get('account_number') or doc_data.get('account_num')
                parameters = doc_data.get('parameters', {})
                incident_id = parameters.get('incident_id')
                
                # Validate required fields
                if not account_number:
                    logger.warning(f"Missing 'account_number' in document: {doc_id}. Full document: {doc}")
                    error_count += 1
                    continue
                if not incident_id:
                    logger.warning(f"Missing 'incident_id' in document: {doc_id}. Full document: {doc}")
                    error_count += 1
                    continue
                    
                # Process the case
                self.process_case(account_number, incident_id)
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing document {doc_id}: {str(e)}")
                continue
                
        logger.info(f"Processed {processed_count} documents, {error_count} errors")
        return processed_count, error_count

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