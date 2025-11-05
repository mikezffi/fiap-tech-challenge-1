from mangum import Mangum
from api.api_v1 import app as fastapi_app

handler = Mangum(fastapi_app)