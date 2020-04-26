from fastapi import FastAPI, Request, HTTPException, status, Response, Cookie, Depends
from pydantic import BaseModel
from typing import Dict
from hashlib import sha256
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasicCredentials, HTTPBasic
import secrets

app = FastAPI()
security = HTTPBasic()
app.secret_key = '2fw98hww018bf13oinfo1830f01oi3bfojbf1eqwfoin13oinfpwvmnwmn98pl26'
patients =[]
app.users={"trudnY":"PaC13Nt"}
app.sessions={}

class HelloNameResp(BaseModel):
    message: str

class MethodResp(BaseModel):
    method: str

class NewPatient(BaseModel):
    name: str=""
    surename: str=""

class Patient(BaseModel):
    id: int
    patient: Dict 

@app.get('/')
def hello_world():
    return {"message": "Hello World during the coronavirus pandemic!"}

@app.get('/welcome')
def hello_known():
	return {"message": "Hello, my patient!"}

def authnt(credentials: HTTPBasicCredentials = Depends(security)):
    iscorr = False
    for username, password in app.users.items():
        iscorr_username = secrets.compare_digest(credentials.username, username)
        iscorr_password = secrets.compare_digest(credentials.password, password)
        if (iscorr_username and iscorr_password):
            iscorr = True
    if not iscorr:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="login / password incorrect",
            headers={"auth": "Basic"},
        )
    session_token = sha256(bytes(f"{credentials.username}{credentials.password}{app.secret_key}", encoding='utf8')).hexdigest()
    app.sessions[session_token]=credentials.username
    return session_token


@app.get("/login")
@app.post("/login")
def login(response: Response, session_token: str = Depends(authnt)):
    response.status_code = status.HTTP_302_FOUND
    response.headers["Location"] = "/welcome"
    response.set_cookie(key="session_token", value=session_token)


@app.get('/hello/{name}', response_model=HelloNameResp)
def hello_name(name: str):
    return HelloNameResp(message=f"hello {name}")

@app.get('/method', response_model=MethodResp)
@app.put('/method', response_model=MethodResp)
@app.delete('/method', response_model=MethodResp)
@app.post('/method', response_model=MethodResp)
def hello_method(request: Request):
    method = request.method
    return MethodResp(method=f"{method}")

@app.post('/patient', response_model=Patient)
def new_patient(data: NewPatient):
    patient_data = data.dict()
    patients.append(patient_data)
    id = len(patients) - 1

    return Patient(id=id, patient=patient_data)

@app.get("/patient/{pk}", response_model=NewPatient)
def get_patient(pk):
    try:
        i = int(pk)

    except:
        raise HTTPException(status_code=400)

    if(i < 0 or i >= len(patients)):
        raise HTTPException(status_code=204)
    
    return NewPatient(**patients[i])
