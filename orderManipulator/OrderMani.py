import pymongo
from pymongo import MongoClient
import time

class OrderProcessor:
    def __init__(self):
        # Initialize MongoDB connection
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['your_database_name']
        self.collection = self.db['your_collection_name']
        
    def process_case(self, account_number, incident_id):
        """Process customer details for case registration"""
        print(f"Processing Case Registration for account: {account_number}, incident: {incident_id}")
        # Add your business logic here

    def get_open_orders(self):
        """Fetch all documents with request_status: 'Open'"""
        return self.collection.find({"request_status": "Open"})

    def process_option_1(self, documents):
        """Handle order_id=1 documents"""
        for doc in documents:
            if doc.get('order_id') == 1:
                try:
                    account_number = doc.get('account_number')
                    incident_id = doc.get('parameters', {}).get('incident_id')
                    
                    if account_number and incident_id:
                        self.process_case(account_number, incident_id)
                    else:
                        print(f"Missing required fields in document: {doc.get('_id')}")
                except Exception as e:
                    print(f"Error processing document {doc.get('_id')}: {str(e)}")

    def show_menu(self):
        """Display user menu"""
        print("\nSelect an option:")
        print("1: Cust Details for Case Registration")
        print("2: Monitor Payment")
        print("3: Monitor Payment Cancel")
        print("4: Close_Monitor_If_No_Transaction")
        return input("Enter option (1-4): ")

    def process_selected_option(self, option, documents):
        """Route processing based on user selection"""
        if option == 1:
            self.process_option_1(documents)
        elif option == 2:
            print("Option 2 selected - Monitor Payment")
            # self.process_option_2(documents)
        elif option == 3:
            print("Option 3 selected - Monitor Payment Cancel")
            # self.process_option_3(documents)
        elif option == 4:
            print("Option 4 selected - Close_Monitor_If_No_Transaction")
            # self.process_option_4(documents)
        else:
            print("Invalid option selected")

    def run(self):
        """Main processing loop"""
        while True:
            try:
                # Get open orders
                open_orders = list(self.get_open_orders())
                
                if not open_orders:
                    print("No open orders found. Waiting...")
                    time.sleep(5)
                    continue
                
                print(f"\nFound {len(open_orders)} open orders")
                
                # Get user input
                try:
                    option = int(self.show_menu())
                except ValueError:
                    print("Please enter a valid number (1-4)")
                    continue
                
                # Process selected option
                self.process_selected_option(option, open_orders)
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\nProgram terminated by user")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
                time.sleep(5)

if __name__ == "__main__":
    processor = OrderProcessor()
    processor.run()