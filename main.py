import sys

from collibra_luigi_client.runner import Runner

from pyi_template_airflow.finale import AirflowFinale
from pyi_template_airflow.story import AirflowStory

# main
if __name__ == '__main__':
    runner = Runner(argv=sys.argv[1:], story=AirflowStory, finale=AirflowFinale).run()
