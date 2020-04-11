import pandas as pd

from TFL_API_Requests import cTFL_Line_Stoppoints_Request
from TFL_API_Requests import cTFL_Lines_for_Modes_Request
from TFL_API_Requests import cTFL_Modes_Request

class cLine():
    "simplified definition of a line"
    def __init__(self,id,name):
        self.id = id
        self.name = name

        self.GetStopPoints()

    def GetStopPoints(self):
        self.stop_point_request = cTFL_Line_Stoppoints_Request(self.id)

    def __str__(self):
        return '%s,%s'%(self.id,self.name)

class cGeoffTechStationCountingChallenge:

    # the rules of Geoffs test is that we only include stops on specific lines that list of lines is as follows, these are
    # the lines shown on the tube map
    valid_modes = ['cable-car', 'dlr', 'overground','river-bus', 'tflrail', 'tram', 'tube']

    def __init__(self):

        # get the full lines for the valid modes
        lines_of_interest_request = cTFL_Lines_for_Modes_Request(self.valid_modes)

        # gte the data for all the lines (and there stop points)
        self.populateTheLines(lines_of_interest_request)

        # convert the stop point data to a panda dataframe
        self.populateStopPoints()
        # built a node data frame by using the hub data in the stop points to merge stop points into nodes
        self.populateTheNodeList()
        # calculate the statistics on the nodes
        self.calculateNodeTypeStatistics()

    def populateTheLines(self,lines_of_interest_request):

        assert isinstance(lines_of_interest_request,cTFL_Lines_for_Modes_Request)

        self.Lines = []
        self.line_ids = []
        for line_data_in_response in lines_of_interest_request.tfl_data_for_line:
            self.line_ids.append(line_data_in_response['id'])
            self.Lines.append(cLine(id=line_data_in_response['id'], name=line_data_in_response['name']))

    def checkAllMode(self):
        # get the list of mdoes supported by the TFL API, this is useful as it allows us to get the syntax for the next step
        # when we extract the list of lines from the modes
        mode_request = cTFL_Modes_Request()
        return mode_request.FullModesName

    def shortenStopPointName(self,stop_point_commonName):

        suffices_to_test = [' Underground Station',' Rail Station',' Tram Stop',' DLR Station', ' Pier.', ' Pier']

        # special case for the two cable car stops
        if (stop_point_commonName == 'Emirates Greenwich Peninsula') or (stop_point_commonName == 'Emirates Royal Docks'):
            return stop_point_commonName

        # special case for the paddington
        if (stop_point_commonName == 'Paddington (H&C Line)-Underground'):
            return 'Paddington'

        for suffix_to_test in suffices_to_test:

            if len(stop_point_commonName) > len(suffix_to_test):
                if stop_point_commonName[-len(suffix_to_test):] == suffix_to_test:
                    return stop_point_commonName[:-len(suffix_to_test)]


        print('failed to find short version of %s'%stop_point_commonName)
        return stop_point_commonName

    @property
    def hub_list(self):
        list_to_return = list(self.stop_point_dataframe['hub'].unique())
        list_to_return.remove('')

        return list_to_return

    def populateStopPoints(self):
        """
        build a dataframe of all the unique Stop Points for the Lines that are identified as valid based on the mode
        :return: 
        """

        # these lists will be the columns of the dataframe
        id_list = []
        hub_list = []
        commonName_list = []
        short_commonName_list = []
        mode_list = []
        line_list = []


        for Line in self.Lines:
            for stop_point in Line.stop_point_request.tfl_data_for_line:

                if stop_point['id'] in id_list:
                    # the data for this stop point is already in te list
                    continue
                else:
                    id_list.append(stop_point['id'])
                    stop_point_commonName = stop_point['commonName']
                    commonName_list.append(stop_point_commonName)

                    lines_at_stop_point = stop_point['lines']
                    line_name_list_at_stop_point = []
                    for line_at_stop_point in lines_at_stop_point:
                        # check each line to see if its mode is on the list of valid modes
                        if line_at_stop_point['id'] in self.line_ids:
                            line_name_list_at_stop_point.append(line_at_stop_point['name'])
                    line_list.append(','.join(line_name_list_at_stop_point))

                    # need to discard references to bus and national rail from the mode list as it is confusing the picture
                    temp_mode_list = stop_point['modes']
                    if 'bus' in temp_mode_list:
                        temp_mode_list.remove('bus')
                    if 'national-rail' in temp_mode_list:
                        temp_mode_list.remove('national-rail')
                    mode_list.append(','.join(temp_mode_list))

                    # make the shortened version of the commonName
                    short_commonName_list.append(self.shortenStopPointName(stop_point_commonName))

                    # hub code is need to link to other stations hub
                    if 'hubNaptanCode' in stop_point.keys():
                        hub_list.append(stop_point['hubNaptanCode'])
                    else:
                        hub_list.append('')

        self.stop_point_dataframe = pd.DataFrame(
            data={'stop_id': id_list,
                  'stop_Name': commonName_list,
                  'short Name' : short_commonName_list,
                  'line': line_list,
                  'modes': mode_list,
                  'hub': hub_list})

        # Geoff has some rules which are slightly different to the definitions used in the data:
        # 1. the cable cars stops are unique nodes not part of their neightbouring underground
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZALRDK','hub'] = ''
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZALGWP','hub'] = ''
        # 2. shadwell overgorund and DLR are not in a hub
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZDLSHA','hub'] = ''
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '910GSHADWEL','hub'] = ''
        # 3. west croyden tram and overground are seperate stops
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '910GWCROYDN','hub'] = ''
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZCRWCR','hub'] = ''
        # 4. paddington district is not part of the paddington hub
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZLUPAC','hub'] = ''
        # 5. hammersmith counts as two tube stations
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZLUHSD','hub'] = ''
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZLUHSC','hub'] = ''
        # 6. new cross and new cross gate are not part of a hub
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '910GNWCRELL','hub'] = ''
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '910GNEWXGTE','hub'] = ''
        # 7 canary wharf is not a single hub
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZDLCAN', 'hub'] = ''
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZLUCYF', 'hub'] = ''
        # 8 west hampstead overground and underground are not a single node
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '940GZZLUWHP', 'hub'] = ''
        self.stop_point_dataframe.loc[self.stop_point_dataframe['stop_id'] == '910GWHMDSTD', 'hub'] = ''

    def populateTheNodeList(self):

        # a node is a concept defined by geoff

        # now need th merge together the stop points that are a not in a hub become a node
        self.nodes = self.stop_point_dataframe.loc[self.stop_point_dataframe['hub'] == '']

        for hub in self.hub_list:

            list_stoppoints_in_hub = self.stop_point_dataframe.loc[self.stop_point_dataframe['hub'] == hub]

            # some hubs only have one entry for reasons unknown, these just merge straight over
            if len(list_stoppoints_in_hub) == 1:
                self.nodes = self.nodes.append(list_stoppoints_in_hub)
                continue

            # take the name of the node from the shortened tube name with the word removed from the end
            try:
                hub_name = list_stoppoints_in_hub.loc[list_stoppoints_in_hub['modes'] == 'tube']['short Name'].values[0]
            except:
                print('can not determine shot name for hub:%s' % hub)

            # sort the mode list so the combined mode field becomes consistent
            mode_list = list(list_stoppoints_in_hub['modes'])
            mode_list.sort()

            new_node = pd.DataFrame(
                data={'stop_id': ','.join(list(list_stoppoints_in_hub['stop_id'])),
                      'stop_Name': ','.join(list(list_stoppoints_in_hub['stop_Name'])),
                      'short Name': hub_name,
                      'line': ','.join(list(list_stoppoints_in_hub['line'])),
                      'modes': ','.join(mode_list),
                      'hub': hub}, index=[1])

            self.nodes = self.nodes.append(new_node, ignore_index=True)

    def calculateNodeTypeStatistics(self):
        """
        calculate the statistics by counting the occurances of the unique values in the modes of the nodes
        :return:
        """
        self.stats = self.nodes['modes'].value_counts()


if __name__ == '__main__':

    GeoffTechStationCountingChallenge = cGeoffTechStationCountingChallenge()
    GeoffTechStationCountingChallenge.stop_point_dataframe.to_csv('stops.csv')

    GeoffTechStationCountingChallenge.nodes.to_csv('nodes.csv')

    print(GeoffTechStationCountingChallenge.stats)










