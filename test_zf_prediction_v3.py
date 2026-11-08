import unittest,random
from datetime import date,timedelta
from zf_prediction_v3 import *
class EngineTests(unittest.TestCase):
    def setUp(self):
        rng=random.Random(8);self.draws=[]
        for i in range(150):
            self.draws.append({'date':(date(2024,1,1)+timedelta(days=i*3)).isoformat(),'numbers':rng.sample(range(1,53),6)})
    def test_unique(self):
        x=prediction_for_date(self.draws,'2026-08-01');self.assertEqual(len(x['predictions']),5)
        self.assertEqual(len(set(map(tuple,x['predictions']))),5)
        self.assertTrue(all(len(set(row))==6 for row in x['predictions']))
    def test_no_future_leakage(self):
        a=prediction_for_date(self.draws,'2024-11-01')
        extended=self.draws+[{'date':'2026-08-01','numbers':[1,2,3,4,5,6]}]
        b=prediction_for_date(extended,'2024-11-01')
        self.assertEqual(a['predictions'],b['predictions'])
    def test_backtest(self):
        result=backtest(self.draws)
        self.assertEqual(result['random']['tested'],130)
        self.assertTrue(all(v['tested']==130 for v in result.values()))
    def test_reproducible(self):
        self.assertEqual(prediction_for_date(self.draws,'2026-08-01')['predictions'],prediction_for_date(self.draws,'2026-08-01')['predictions'])
if __name__=='__main__':unittest.main()
