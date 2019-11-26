from google.cloud import firestore, exceptions
import logging

logging.basicConfig(level=logging.DEBUG)


class Device(object):
    def __init__(self):
        self.db = firestore.Client()

    def get(self, docid):
        ref = self.db.collection(u'devices').document(docid)
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
            self.db.collection(u'devices').document(docid).set(update_data)
        except Exception as e:
            logging.debug(f"Unable to update: {e}")
            raise Exception(f"Unable to update record. {docid}")

    def query(self, query):
        ref = self.db.collection(u'devices')
        logging.debug(f"Querying data: {query}.")
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
        return result_dict


class Query(object):
    def __init__(self, field, op_string, value):
        self.field = field
        self.op_string = op_string
        self.value = value
