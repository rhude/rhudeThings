from google.cloud import firestore, exceptions
import logging

logging.basicConfig(level=logging.DEBUG)
import secrets


class User(object):
    def __init__(self):
        self.db = firestore.Client()

    def get(self, docid):
        ref = self.db.collection(u'users').document(docid)
        doc = None
        try:
            doc = ref.get()
        except exceptions.NotFound:
            logging.debug(f"Document: {docid} not found.")
        return doc.to_dict()

    def update(self, docid, data):
        update_data = self.get(docid)
        logging.debug(f"Existing data: {update_data}.")
        update_data.update(data)
        logging.debug(f"Updated data: {update_data}.")
        logging.debug(f"Writing to docid: {docid}")
        try:
            self.db.collection(u'users').document(docid).set(update_data)
        except Exception as e:
            logging.debug(f"Unable to update: {e}")
            raise Exception(f"Unable to update record. {docid}")

    def query(self, query):
        ref = self.db.collection(u'users')
        logging.debug(f"Querying data.")
        query_ref = ref.where(field_path=query.field, op_string=query.op_string, value=query.value)
        docs = query_ref.stream()
        results = []
        for doc in docs:
            logging.debug(f"Document id: {doc.id}")
            doc_data = doc.to_dict()
            doc_result = {
                doc.id: doc_data
            }
            results.append(doc_result)
        result_dict = {
            'results': results
        }
        logging.debug(f"Query returned: {result_dict}.")
        return result_dict

    def login(self, userid, password):
        ref = self.db.collection(u'users')
        logging.debug(f"Searching for {userid}")
        query_ref = ref.where(field_path='userid', op_string='==', value=userid).limit(1)
        docs = query_ref.stream()
        for doc in docs:
            logging.debug(f"Document id: {doc.id}")
            doc_data = doc.to_dict()
            if doc_data["password"] == password:
                logging.debug(f"User {userid} logged in.")
                sessionid = self.update_session(doc.id)
                if sessionid is not False:
                    return sessionid
                else:
                    raise Exception("Username or password mismatch.")
            else:
                logging.debug(f"Username or password mismatch.")
                raise Exception("Username or password mismatch.")

        logging.debug(f"User {userid} not found.")
        raise Exception("Username not found")


    def update_session(self, docid):
        ref = self.db.collection(u'users')
        sessionid = make_token()
        logging.debug(f"Updating session id for {docid}, token: {sessionid}.")
        data = {
            'sessionid': sessionid
        }
        try:
            self.update(docid=docid, data=data)
        except Exception as e:
            logging.debug(f"Exception: e")
            raise Exception("Unable to update sessionid.")
            return False
        return sessionid


    def check_session(self, sessionid):
        ref = self.db.collection(u'users')
        logging.debug(f"Checking sessionid: {sessionid}")
        q = Query(
            field='sessionid',
            op_string='==',
            value=sessionid
        )
        results = self.query(q)
        logging.debug(f"SessionID results: {results}")
        if len(results['results']) > 0:
            user_info = results['results']
            return user_info
        else:
            return False

    def check_token(self, access_token):
        ref = self.db.collection(u'users')
        logging.debug(f"Checking access token: {access_token}")
        q = Query(
            field='access_token',
            op_string='==',
            value=access_token
        )
        results = self.query(q)
        logging.debug(f"AccessToken results: {results}")
        if len(results['results']) > 0:
            user_info = results['results']
            return user_info
        else:
            return False


class Query(object):
    def __init__(self, field, op_string, value):
        self.field = field
        self.op_string = op_string
        self.value = value


def make_token():
    """
    Creates a cryptographically-secure, URL-safe string
    """
    return secrets.token_urlsafe(16)