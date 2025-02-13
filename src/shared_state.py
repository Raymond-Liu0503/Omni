class SharedState:
    def __init__(self):
        self.latest_results = "Welcome to Omni! What do you want to do today?"

    def update_latest_results(self, results):
        self.latest_results = results

    def get_latest_results(self):
        return self.latest_results
    
    def clear_cache(self):
        self.latest_results = None

shared_state = SharedState()