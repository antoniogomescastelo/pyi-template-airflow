import json
import logging

import luigi
from collibra_luigi_client.story import Story
from requests import Session
from requests.auth import HTTPBasicAuth


class AirflowStory(Story):
    runner = luigi.Parameter()
    request = luigi.Parameter()

    def run(self):
        logger = logging.getLogger(__name__)

        with self.input().open() as infile:
            input = json.loads(infile.read())

        # check
        requiredElements = ['Community', 'SystemAsset', 'DagName']

        notfoundElements = list(filter(lambda x: True if x not in input else False, requiredElements))

        [logger.warn("keyerror '%s', skip %s", x, input['Id']) for x in notfoundElements]

        if len(notfoundElements): raise KeyError(",".join(notfoundElements))

        # get community
        try:
            uuid = input['Community'][0]['CommunityAttributeValue']

            community = self.runner.collibraClient.get_community(uuid)

        except Exception as e:
            logger.error("community id wrong or no asset found")
            raise (e)

        # get system asset
        try:
            uuid = input['SystemAsset'][0]['SystemAssetAttributeValue']

            systemAsset = self.runner.collibraClient.get_asset(uuid)

        except Exception as e:
            logger.error("system asset id wrong or no asset found")
            raise (e)

        # get airflow
        try:
            airflow = {
                "url": self.runner.config['airflow']['url'],
                "username": self.runner.config['airflow']['username'],
                "password": self.runner.config['airflow']['password']
            }

        except Exception as e:
            logger.error(f"invalid airflow configuration {e.args[0]}")
            raise (e)

        session = Session()

        session.auth = HTTPBasicAuth(airflow['username'], airflow['password'])

        # get airflow dags
        dags = {d['DagNameAttributeValue']: {} for d in input['DagName']}

        # get airflow dag details
        for d in dags:
            try:
                response = session.get(airflow['url'] + '/dags/' + d + '/details', headers={'accept': 'application/json'})

                logger.debug(f"dags: {d}")

                dags[d] = response.json()

            except Exception as e:
                pass

            # enrich with the dag file content
            try:
                response = session.get(airflow['url'] + '/dagSources/' + dags[d]['file_token'], headers={'accept': 'application/json'})

                dags[d]['content'] = '<pre>' + response.json()['content'] + '</pre>'

            except Exception as e:
                pass


            # enrich with the dag tasks details
            try:
                response = session.get(airflow['url'] + '/dags/' + d + '/tasks', headers={'accept': 'application/json'})

                logger.debug("tasks: %s %s", d, list(map(lambda i: i['task_id'], response.json()['tasks'])))

                dags[d]['tasks'] = {t['task_id']: t for t in response.json()['tasks']}

            except Exception as e:
                pass


        # iterate dags and tasks
        entries = []
        for dag in dags.values():
            tags=[]

            attributes={}

            assetName  = f"{systemAsset['name']}>{dag['dag_id']}"

            domainName = f"{systemAsset['name']} > {dag['dag_id']}"

            # add dag attributes and tags
            properties = [('description','Description'), ('fileloc','fileloc'),('content','content'),  ('is_active','is_active'), ('owners', 'owners')] 

            [attributes.update({property[1]: dag[property[0]] if type(dag[property[0]])==list else [dag[property[0]]]}) for property in properties]

            [[tags.append(f"{k}:{v}") for k, v in tag.items()] for tag in dag['tags']]
            
            # register domain and dag asset
            entries.append(self.runner.collibraClient.get_import_entry(entryName=domainName, entryType='Physical Data Dictionary', resourceType='Domain', communityName=community['name']))

            entries.append(self.runner.collibraClient.get_import_entry(entryName=assetName, entryType='DAG', resourceType='Asset', domainName=domainName, communityName=community['name'], attributes=attributes, tags=tags))


            for task in dag['tasks'].values():
                attributes={}

                # add task attributes 
                dagName =  f"{systemAsset['name']}>{dag['dag_id']}"

                taskName = f"{systemAsset['name']}>{dag['dag_id']}>{task['task_id']}"

                properties = [('downstream_task_ids','downstream_task_ids'), ('operator_name','operator_name'), ('owner','owners'), ('priority_weight','priority_weight'), ('queue','queue'), ('trigger_rule','trigger_rule')] 

                [attributes.update({property[1]: task[property[0]] if type(task[property[0]])==list else [task[property[0]]]}) for property in properties]

                attributes['class_ref'] = [f"{k}:{v}" for k,v in task['class_ref'].items()]

                # add task relationships
                containedIn=[]

                containedIn.append(self.runner.collibraClient.get_import_entry_identifier(dagName, domainName, community['name']))
                
                sources=[]

                for source in attributes['downstream_task_ids']:
                    sourceName = f"{systemAsset['name']}>{dag['dag_id']}>{source}"

                    sources.append(self.runner.collibraClient.get_import_entry_identifier(sourceName, domainName, community['name']))


                relations={}

                relations.update({'bfb0a713-0325-4cfc-b5d6-cd6ff5cbbf42:SOURCE': containedIn, '8a75700e-d091-4b84-a859-1e457986fc77:TARGET': sources})

                # register task asset
                entries.append(self.runner.collibraClient.get_import_entry(entryName=taskName, entryType='DAG Task', resourceType='Asset', domainName=domainName, communityName=community['name'], attributes=attributes, relations=relations))


        # get document
        clusters = '[["Domain:Physical Data Dictionary", "Asset:DAG"], ["Asset:DAG Task"], ["relations:8a75700e-d091-4b84-a859-1e457986fc77:TARGET"]]'

        document = f"{{\"clusters\":{clusters} , \"document\":[{','.join(list(map(str, entries)))}]}}"

        # write
        with self.output().open("w") as outfile:
            outfile.write(document)

            logger.info(f"writing story output file: {outfile.name}")

