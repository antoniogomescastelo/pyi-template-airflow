import luigi
from collibra_luigi_client.finale import Finale
from collibra_luigi_client.service.beam import BeamClient


class AirflowFinale(Finale):
    runner = luigi.Parameter()

    def run(self):
        super().run()

        BeamClient(runner=self.runner).run()
