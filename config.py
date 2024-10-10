import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')
    API_KEY = "live_50301f9499945c88956abe134aef5b51af46eae91665acfefe42f9f45fc35951efe8d04e6d233bd35cf2fabdeb93fb0d"
    API_URL = "https://open.api.nexon.com/fconline/v1/"