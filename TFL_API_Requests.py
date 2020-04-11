"""
module that using the TFL API to grab data for determining the makeup of the network.
"""
import requests

class cTFL_DataRequest:
    """ This class makes a general data request to the TFL API and handles the  http request and its response"""
    def __init__(self,URL_suffix):

        resp = requests.get('https://api.tfl.gov.uk/'+URL_suffix)
        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiError('GET /tasks/ {}'.format(resp.status_code))

        self.tfl_data_for_line = resp.json()

class cTFL_Line_Stoppoints_Request(cTFL_DataRequest):
    def __init__(self,line_id):

        self.line_id = line_id

        super().__init__('line/%s/stoppoints'%line_id)

class cTFL_Route_Request(cTFL_DataRequest):
    def __init__(self,toplace,fromplace):
        super().__init__('%s/to%s'%(fromplace,toplace))

class cTFL_Lines_for_Modes_Request(cTFL_DataRequest):
    def __init__(self,modes):

        assert isinstance(modes,list)
        modes_str = ','.join(modes)

        super().__init__('Line/Mode/'+modes_str)

class cTFL_Modes_Request(cTFL_DataRequest):
    def __init__(self):
        super().__init__('Line/Meta/Modes')

    @property
    def FullModesName(self):

        list_to_return = []
        for mode in self.tfl_data_for_line:
            list_to_return.append(mode['modeName'])

        return list_to_return