import logging
from device import Device, Query
logging.basicConfig(level=logging.DEBUG)

INTENTS = {
    'action.devices.SYNC': 'sync',
    'action.devices.QUERY': 'query',
    'action.devices.EXECUTE': 'execute',
    'action.devices.DISCONNECT': 'disconnect'
}

class Intent(object):
    def __init__(self, docid):
        self.request_id = None
        self.intent = None
        self.docid = docid

    def get(self, payload):
        # Unpack json and get intent.
        request_id = payload['requestId']
        intent = payload['inputs'][0]['intent']
        self.request_id = request_id
        self.intent = intent
        return True

    def run(self, intent, payload):
        return getattr(self, INTENTS[intent])(payload)

    def sync(self, payload):
        # Unpack request id.
        request_id = payload['requestId']
        self.request_id = request_id

        # Get all devices assigned to user.
        device = Device()
        query = Query(
            field='assigned_user',
            op_string='==',
            value=self.docid
        )
        device_results = device.query(query)['results']
        logging.debug(f"Found devices: {device_results}")

        # Build device payload.
        devices_payload = []
        for d in device_results:
            device_id = list(d.keys())[0]
            device_payload = d[device_id]['attributes']['google']
            device_payload.update(
                {
                    'id': device_id
                }
            )
            devices_payload.append(device_payload)

        response_payload = {
            'requestId': request_id,
            'payload': {
                'agentUserId': self.docid,
                'devices': devices_payload
            }
        }
        return response_payload

    def query(self, payload):
        # Unpack request id.
        request_id = payload['requestId']
        self.request_id = request_id

        #Get the device state from the db for this user.
        device = Device()
        query = Query(
            field='assigned_user',
            op_string='==',
            value=self.docid
        )
        device_results = device.query(query)['results']
        logging.debug(f"Found devices: {device_results}")

        query_device_state = []
        for query_device in payload['inputs'][0]['payload']['devices']:
            device_id = query_device['id']
            try:
                current_state = device_results[0][device_id]['state']
            except:
                current_state = {}
            query_device_state.append({
                    device_id: current_state
                })
        response_payload = {
            'requestId': request_id,
            'payload': {
                'agentUserId': self.docid,
                'devices': query_device_state
            }
        }
        return response_payload

    def execute(self, payload):
        # Unpack request id.
        request_id = payload['requestId']
        self.request_id = request_id

        # Unpack payload into commands.
        query_commands = payload['inputs'][0]['payload']['commands'][0]  # I feel like this is wrong but google did it.
        query_devices = query_commands['devices']
        query_execution = query_commands['execution'][0]

        # Get the device state from the db for this user.
        device = Device()
        query = Query(
            field='assigned_user',
            op_string='==',
            value=self.docid
        )
        device_results = device.query(query)['results']
        logging.debug(f"Found devices: {device_results}")
        query_device_state_success = []
        query_device_state_failed = []
        for query_device in query_devices:
            device_id = query_device['id']
            logging.debug(f"Execution: {query_execution}, device: {device_id}")
            try:
                current_state = device_results[0][device_id]['state']
                logging.debug(f"Current state {device_id} is {current_state}")
                current_state.update(query_execution['params'])
                try:
                    device.update(device_id, {'state': current_state})
                    logging.debug(f"Updated state: {current_state}")
                    current_state.update(
                        {
                            'online': True
                        }
                    )
                    query_device_state_success.append(
                        {
                            'ids': [device_id],
                            'status': "SUCCESS",
                            'states': current_state
                        }
                    )

                except Exception as e:
                    logging.debug(f"Unable to update device state: {device_id}")
                    query_device_state_failed.append(
                        {
                            'ids': [device_id],
                            'status': "FAILED",
                        }
                    )
            except Exception as e:
                logging.debug(f"Exception: {e}")
                query_device_state_failed.append(
                    {
                        'ids': [device_id],
                        'status': "FAILED",
                    }
                )
        query_state = query_execution['params']
        query_state.update({"states": {"online": True}})
        response_payload = {
            'requestId': request_id,
            "payload": {
                "commands":
                    query_device_state_success + query_device_state_failed
            }
        }
        return response_payload

    def disconnect(self, payload):
        # Unpack request id.
        request_id = payload['requestId']
        self.request_id = request_id

        response = {}
        return response
