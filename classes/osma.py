import boto3
import requests
import json
from dateutil.relativedelta import relativedelta
import datetime

class Osma:

    def __init__(self, region='us-east-1', profile_name='default'):
        self.region = region
        self.profile_name = profile_name
        self.accessToken = None

    def authenticate_and_get_access_token_via_api(self, username, password):

        url = "https://mrb5y4lp39.execute-api.us-east-1.amazonaws.com/api/login"
        payload = json.dumps({
            "username": username,
            "password": password
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        self.user = username
        self.pwd = password
        # print("Log in success")
        # print("Access token:", resp['AuthenticationResult']['AccessToken'])
        # print("ID token:", resp['AuthenticationResult']['IdToken'])
        resp = json.loads(response.text)
        if resp['statusCode'] == 200:
            self.accessToken = resp['body']['AccessToken']
            return self.accessToken != None

        return False
        # return resp['AuthenticationResult']['AccessToken']!=None

    def authenticate_and_get_access_token(self, username, password):

    # client = boto3.client('cognito-idp',region_name=REGION)
            client = boto3.session.Session(profile_name='default').client('cognito-idp', region_name=REGION)

            resp = client.admin_initiate_auth(
                UserPoolId=USER_POOL_ID,
                ClientId=APP_CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password
                }
            )

            self.user = username
            self.pwd = password
            # print("Log in success")
            # print("Access token:", resp['AuthenticationResult']['AccessToken'])
            # print("ID token:", resp['AuthenticationResult']['IdToken'])
            self.accessToken = resp['AuthenticationResult']['AccessToken']

            return resp['AuthenticationResult']['AccessToken'] != None

    def getDatosVariableEnergy(self, idVariable, fechaInicio, fechaFin, interval):

        dateInicio = fechaInicio.strftime("%Y-%m-%d")
        dateFin = fechaFin.strftime("%Y-%m-%d")

        horaInicio = fechaInicio.strftime("%H:%M")
        horaFin = fechaFin.strftime("%H:%M")

        url = "https://27xakwexw4.execute-api.us-east-1.amazonaws.com/latest/getDatosEnergy/%d/%s/%s/%s/%s/%s/TRUE/" % (
            idVariable, dateInicio, dateFin, interval, horaInicio, horaFin)

        payload = {}
        headers = {
            'user_token': self.accessToken
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        jsonData = response.json()

        if jsonData['result']['status'] == "OK":
            varData = {}
            varData['date'] = jsonData['result']['dateTime']
            varData['values'] = jsonData['result']['values']
            varData['variable'] = jsonData['result']['variable']
            return varData
        return None

    def getDatosVariable(self, idVariable, fechaInicio, fechaFin, interval,
                         monthInterval=-1):

        if monthInterval < 1:
            return self.getDatosVariableNotDivided(idVariable, fechaInicio, fechaFin, interval)
        else:
            allData = None
            fini = fechaInicio

            while True:
                ffin = fechaFin
                fendTemp = fini + relativedelta(months=monthInterval)

                if fendTemp < ffin:
                    ffin = fendTemp

                response = self.getDatosVariableNotDivided(idVariable, fini, ffin, interval)

                if response != None:
                    if allData == None:
                        allData = response
                    else:
                        allData['values'].extend(response['values'])
                        allData['date'].extend(response['date'])

                fini = fendTemp

                if fendTemp >= fechaFin:
                    break

            return allData

    def getDatosVariableNotDivided(self, idVariable, fechaInicio, fechaFin, interval):
        dateInicio = fechaInicio.strftime("%Y-%m-%d")
        dateFin = fechaFin.strftime("%Y-%m-%d")
        horaInicio = fechaInicio.strftime("%H:%M")
        horaFin = fechaFin.strftime("%H:%M")

        url = "https://n7ry336c1g.execute-api.us-east-1.amazonaws.com/latest/getDatosAurora/%d/%s/%s/%s/%s/%s/TRUE/" % (
            idVariable, dateInicio, dateFin, interval, horaInicio, horaFin)

        payload = {}
        headers = {
            'user_token': self.accessToken
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        jsonData = response.json()

        if 'result' in jsonData and jsonData['result']['status'] == "OK":
            varData = {}
            varData['date'] = jsonData['result']['dateTime']
            varData['values'] = jsonData['result']['values']
            varData['values'] = [float(i) for i in varData['values']]
            varData['variable'] = jsonData['result']['variable']
            return varData
        return None

if __name__ == "__main__":

    # Creamos el objeto Osma y Loggin
    osma = Osma()
    loginSuccesfull = osma.authenticate_and_get_access_token_via_api("scripts@osma.com.uy", "0sm4.5cript5")

    if loginSuccesfull:
        print("login Succesfull")

        # Ajustamos fecha para el ultimo dia
        fecha_fin = datetime.datetime.now()#datetime.datetime(2017, 10, 17, 23, 59)
        fecha_inicio = fecha_fin - datetime.timedelta(days = 2)
        print('fechaInicio = {}'.format(fecha_inicio))
        print('fechaFin = {}'.format(fecha_fin))

        # Obtengo datos de Id
        interval = "MIN" # HOUR, DAY, MONTH
        id = 7847 # ID VARIABLE METADATA
        data_raw = osma.getDatosVariable(id, fecha_inicio, fecha_fin, interval)

        date = data_raw['date']
        values = data_raw['values']

        print(data_raw)