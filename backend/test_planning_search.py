import unittest
from planning.search import SearchCandidate,best_of_n,beam_search,monte_carlo_tree_search
from planning.meta_planner import PlanningContext,allocate_planning_compute,compare_planning_strategies

class SearchTests(unittest.TestCase):
    def test_best_of_n(self):
        r=best_of_n([SearchCandidate("a",("x",),1),SearchCandidate("b",("y",),3)],1)
        self.assertEqual(r.candidates[0].candidate_id,"b")
        self.assertTrue(r.truncated)
    def test_best_of_n_invalid(self):
        with self.assertRaises(ValueError): best_of_n([],0)
    def test_beam_finds_goal(self):
        graph={"s":[("a","x",0),("b","y",0)],"x":[("finish","goal",0)]}
        r=beam_search("s",lambda s:graph.get(s,[]),lambda s:{"s":0,"x":1,"y":2,"goal":10}[s],beam_width=2,max_depth=2)
        self.assertTrue(any(c.metadata["state"]=="goal" for c in r.candidates))
    def test_beam_invalid_width(self):
        with self.assertRaises(ValueError): beam_search("s",lambda s:[],lambda s:0,beam_width=0)
    def test_mcts_selects_best(self):
        g={"root":[("left","l",0),("right","r",0)],"l":[("end","bad",0)],"r":[("end","good",0)]}
        r=monte_carlo_tree_search("root",g,{"bad":0,"good":10},iterations=100)
        self.assertEqual(r.candidates[0].metadata["state"],"r")
    def test_mcts_invalid_iterations(self):
        with self.assertRaises(ValueError): monte_carlo_tree_search("s",{}, {},iterations=0)
    def test_meta_risk(self):
        self.assertEqual(allocate_planning_compute(PlanningContext(2,4,.9,100)).strategy,"mcts")
    def test_meta_complexity(self):
        self.assertEqual(allocate_planning_compute(PlanningContext(20,10,.2,500)).strategy,"beam")
    def test_meta_zero_budget(self):
        r=allocate_planning_compute(PlanningContext(1,1,0,0))
        self.assertEqual((r.strategy,r.budget),("greedy",0))
    def test_compare(self):
        self.assertEqual(compare_planning_strategies({"beam":.7,"mcts":.9}),"mcts")

if __name__=="__main__": unittest.main()
