#!/usr/bin/env python3 -m unittest tests.geneticminer_test
# Author: Maximilian Josef Frank (https://orcid.org/0000-0002-0714-7748)

import unittest
from pm4py import save_vis_petri_net
from pm4py.algo.discovery.genetic import algorithm as geneticminer
from pm4py.algo.discovery.genetic.util import iset
from pm4py.objects.conversion.genetic_matrix.variants.to_petri_net import apply as matrix2petrinet
from pm4py.objects.genetic_matrix.obj import GeneticMatrix
from pm4py.objects.petri_net.obj import PetriNet
from pm4py.objects.petri_net import utils


class TestGeneticMiner(unittest.TestCase):
        def test_matrix2petrinet_or(self):
                I = {
                        "A": [],
                        "B": [{"A"}],
                        "C": [{"A"}],
                        "D": [{"B","C"}]
                }
                O = {
                        "A": [{"B","C"}],
                        "B": [{"D"}],
                        "C": [{"D"}],
                        "D": []
                }
                for t in I:
                        I[t] = [iset(s) for s in I[t]]
                        O[t] = [iset(s) for s in O[t]]
                res,_,_ = self._subject(I, O, T=I.keys())
#               self._visualise(res)
                cmp = """places: [ ({'A'}, {'B', 'C'}), ({'B', 'C'}, {'D'}), i, o ]
transitions: [ (A, None), (B, None), (C, None), (D, None) ]
arcs: [ (A, None)->({'A'}, {'B', 'C'}), (B, None)->({'B', 'C'}, {'D'}), (C, None)->({'B', 'C'}, {'D'}), (D, None)->o, ({'A'}, {'B', 'C'})->(B, None), ({'A'}, {'B', 'C'})->(C, None), ({'B', 'C'}, {'D'})->(D, None), i->(A, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_or2(self):
                I = {
                        "A": [],
                        "B": [],
                        "C": [{"A","B"}],
                        "D": [{"A","B"}]
                }
                O = {
                        "A": [{"C","D"}],
                        "B": [{"C","D"}],
                        "C": [],
                        "D": []
                }
                for t in I:
                        I[t] = [iset(s) for s in I[t]]
                        O[t] = [iset(s) for s in O[t]]
                res,_,_ = self._subject(I, O, T=I.keys())
#               self._visualise(res)
                cmp = """places: [ ({'A', 'B'}, {'C', 'D'}), i, o ]
transitions: [ (A, None), (B, None), (C, None), (D, None) ]
arcs: [ (A, None)->({'A', 'B'}, {'C', 'D'}), (B, None)->({'A', 'B'}, {'C', 'D'}), (C, None)->o, (D, None)->o, ({'A', 'B'}, {'C', 'D'})->(C, None), ({'A', 'B'}, {'C', 'D'})->(D, None), i->(A, None), i->(B, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_andOrCross(self):
                I = {
                        "A": [],
                        "B": [],
                        "C": [{"A"},{"B"}],
                        "D": [{"A","B"}]
                }
                O = {
                        "A": [{"C","D"}],
                        "B": [{"C"},{"D"}],
                        "C": [],
                        "D": []
                }
                for t in I:
                        I[t] = [iset(s) for s in I[t]]
                        O[t] = [iset(s) for s in O[t]]
                res,_,_ = self._subject(I, O, T=I.keys())
#               self._visualise(res)
                cmp = """places: [ i, i('C', {'A'}), i('C', {'B'}), i('D', {'A', 'B'}), o, o('A', {'C', 'D'}), o('B', {'C'}), o('B', {'D'}) ]
transitions: [ (, None), (, None), (, None), (, None), (A, None), (B, None), (C, None), (D, None) ]
arcs: [ (, None)->i('C', {'A'}), (, None)->i('C', {'B'}), (, None)->i('D', {'A', 'B'}), (, None)->i('D', {'A', 'B'}), (A, None)->o('A', {'C', 'D'}), (B, None)->o('B', {'C'}), (B, None)->o('B', {'D'}), (C, None)->o, (D, None)->o, i('C', {'A'})->(C, None), i('C', {'B'})->(C, None), i('D', {'A', 'B'})->(D, None), i->(A, None), i->(B, None), o('A', {'C', 'D'})->(, None), o('A', {'C', 'D'})->(, None), o('B', {'C'})->(, None), o('B', {'D'})->(, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_orCross(self):
                # Fig. 2 in https://doi.org/10.1007/11494744_5
                I = {
                        "A": [],
                        "B": [],
                        "C": [{"A"}],
                        "D": [{"A","B"}]
                }
                O = {
                        "A": [{"C","D"}],
                        "B": [{"D"}],
                        "C": [],
                        "D": []
                }
                for t in I:
                        I[t] = [iset(s) for s in I[t]]
                        O[t] = [iset(s) for s in O[t]]
                res,_,_ = self._subject(I, O, T=I.keys())
#               self._visualise(res)
                cmp = """places: [ i, i('C', {'A'}), i('D', {'A', 'B'}), o, o('A', {'C', 'D'}), o('B', {'D'}) ]
transitions: [ (, None), (, None), (, None), (A, None), (B, None), (C, None), (D, None) ]
arcs: [ (, None)->i('C', {'A'}), (, None)->i('D', {'A', 'B'}), (, None)->i('D', {'A', 'B'}), (A, None)->o('A', {'C', 'D'}), (B, None)->o('B', {'D'}), (C, None)->o, (D, None)->o, i('C', {'A'})->(C, None), i('D', {'A', 'B'})->(D, None), i->(A, None), i->(B, None), o('A', {'C', 'D'})->(, None), o('A', {'C', 'D'})->(, None), o('B', {'D'})->(, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_and(self):
                I = {
                        "A": [],
                        "B": [{"A"}],
                        "C": [{"A"}],
                        "D": [{"B"},{"C"}]
                }
                O = {
                        "A": [{"B"},{"C"}],
                        "B": [{"D"}],
                        "C": [{"D"}],
                        "D": []
                }
                for t in I:
                        I[t] = [iset(s) for s in I[t]]
                        O[t] = [iset(s) for s in O[t]]
                res,_,_ = self._subject(I, O, T=I.keys())
#               self._visualise(res)
                cmp = """places: [ ({'A'}, {'B'}), ({'A'}, {'C'}), ({'B'}, {'D'}), ({'C'}, {'D'}), i, o ]
transitions: [ (A, None), (B, None), (C, None), (D, None) ]
arcs: [ (A, None)->({'A'}, {'B'}), (A, None)->({'A'}, {'C'}), (B, None)->({'B'}, {'D'}), (C, None)->({'C'}, {'D'}), (D, None)->o, ({'A'}, {'B'})->(B, None), ({'A'}, {'C'})->(C, None), ({'B'}, {'D'})->(D, None), ({'C'}, {'D'})->(D, None), i->(A, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_and2(self):
                I = {
                        "A": [],
                        "B": [],
                        "C": [{"A"},{"B"}],
                        "D": [{"A"},{"B"}]
                }
                O = {
                        "A": [{"C"},{"D"}],
                        "B": [{"C"},{"D"}],
                        "C": [],
                        "D": []
                }
                for t in I:
                        I[t] = [iset(s) for s in I[t]]
                        O[t] = [iset(s) for s in O[t]]
                res,_,_ = self._subject(I, O, T=I.keys())
#               self._visualise(res)
                cmp = """places: [ ({'A'}, {'C'}), ({'A'}, {'D'}), ({'B'}, {'C'}), ({'B'}, {'D'}), i, o ]
transitions: [ (A, None), (B, None), (C, None), (D, None) ]
arcs: [ (A, None)->({'A'}, {'C'}), (A, None)->({'A'}, {'D'}), (B, None)->({'B'}, {'C'}), (B, None)->({'B'}, {'D'}), (C, None)->o, (D, None)->o, ({'A'}, {'C'})->(C, None), ({'A'}, {'D'})->(D, None), ({'B'}, {'C'})->(C, None), ({'B'}, {'D'})->(D, None), i->(A, None), i->(B, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_full(self):
                # Fig. 3 in https://doi.org/10.1007/11494744_5
                I = {
                        "A": [],
                        "B": [{"A"}],
                        "C": [{"A"}],
                        "D": [{"A"}],
                        "E": [{"B"}, {"C"}],
                        "F": [{"B"}, {"D"}],
                        "G": [{"E"}, {"F"}]
                }
                O = {
                        "A": [{"B"}, {"C", "D"}],
                        "B": [{"E", "F"}],
                        "C": [{"E"}],
                        "D": [{"F"}],
                        "E": [{"G"}],
                        "F": [{"G"}],
                        "G": []
                }
                transitions = list(I.keys())
                res,_,_ = self._subject(I, O, T=transitions)
#               self._visualise(res, file="full.png")
                cmp = """places: [ ({'A'}, {'B'}), ({'A'}, {'C', 'D'}), ({'B'}, {'E', 'F'}), ({'C'}, {'E'}), ({'D'}, {'F'}), ({'E'}, {'G'}), ({'F'}, {'G'}), i, o ]
transitions: [ (A, None), (B, None), (C, None), (D, None), (E, None), (F, None), (G, None) ]
arcs: [ (A, None)->({'A'}, {'B'}), (A, None)->({'A'}, {'C', 'D'}), (B, None)->({'B'}, {'E', 'F'}), (C, None)->({'C'}, {'E'}), (D, None)->({'D'}, {'F'}), (E, None)->({'E'}, {'G'}), (F, None)->({'F'}, {'G'}), (G, None)->o, ({'A'}, {'B'})->(B, None), ({'A'}, {'C', 'D'})->(C, None), ({'A'}, {'C', 'D'})->(D, None), ({'B'}, {'E', 'F'})->(E, None), ({'B'}, {'E', 'F'})->(F, None), ({'C'}, {'E'})->(E, None), ({'D'}, {'F'})->(F, None), ({'E'}, {'G'})->(G, None), ({'F'}, {'G'})->(G, None), i->(A, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_mixed(self):
                I = {
                        'A': [{'B', 'Y'}],
                        'B': [{'C'}],
                        'C': [{'Y'}],
                        'D': [{'Y'}],
                        'E': [{'F'}],
                        'F': [{'G'}],
                        'G': [{'H'}],
                        'H': [{'Y'}],
                        'I': [{'I'}],
                        'J': [{'I'}],
                        'K': [{'Z'}, {'S'}],
                        'L': [{'L'}],
                        'M': [{'L'}],
                        'N': [{'O'}],
                        'O': [{'L', 'X'}],
                        'P': [{'Q'}],
                        'Q': [{'X'}],
                        'R': [{'R', 'I'}],
                        'S': [{'R'}],
                        'T': [{'L', 'Y'}],
                        'U': [{'U'}, {'Y'}],
                        'V': [{'V', 'X'}],
                        'W': [{'L', 'W'}],
                        'X': [],
                        'Y': [],
                        'Z': [{'X'}]
                }
                O = {
                        'B': [{'A'}],
                        'Y': [{'A'}, {'D', 'T', 'U', 'C'}, {'H'}],
                        'C': [{'B'}],
                        'F': [{'E'}],
                        'G': [{'F'}],
                        'H': [{'G'}],
                        'I': [{'J', 'R'}, {'I'}],
                        'Z': [{'K'}],
                        'L': [{'M', 'O', 'T', 'L'}, {'W'}],
                        'O': [{'N'}],
                        'X': [{'O', 'Q', 'Z', 'V'}],
                        'Q': [{'P'}],
                        'R': [{'S'}, {'R'}],
                        'U': [{'U'}],
                        'V': [{'V'}],
                        'W': [{'W'}],
                        'P': [],
                        'N': [],
                        'T': [],
                        'M': [],
                        'D': [],
                        'A': [],
                        'E': [],
                        'K': [],
                        'S': [{'K'}],
                        'J': []
                }
                transitions = list(set(I.keys()) & set(O.keys()))
                res,_,_ = self._subject(I, O, T=transitions)
#               self._visualise(res)
                cmp = """places: [ ({'C'}, {'B'}), ({'F'}, {'E'}), ({'G'}, {'F'}), ({'H'}, {'G'}), ({'O'}, {'N'}), ({'Q'}, {'P'}), ({'S'}, {'K'}), ({'Z'}, {'K'}), i, i('A', {'B', 'Y'}), i('C', {'Y'}), i('D', {'Y'}), i('H', {'Y'}), i('I', {'I'}), i('J', {'I'}), i('L', {'L'}), i('M', {'L'}), i('O', {'L', 'X'}), i('Q', {'X'}), i('R', {'I', 'R'}), i('S', {'R'}), i('T', {'L', 'Y'}), i('U', {'U'}), i('U', {'Y'}), i('V', {'V', 'X'}), i('W', {'L', 'W'}), i('Z', {'X'}), o, o('B', {'A'}), o('I', {'I'}), o('I', {'J', 'R'}), o('L', {'L', 'M', 'O', 'T'}), o('L', {'W'}), o('R', {'R'}), o('R', {'S'}), o('U', {'U'}), o('V', {'V'}), o('W', {'W'}), o('X', {'O', 'Q', 'V', 'Z'}), o('Y', {'A'}), o('Y', {'C', 'D', 'T', 'U'}), o('Y', {'H'}) ]
transitions: [ (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (A, None), (B, None), (C, None), (D, None), (E, None), (F, None), (G, None), (H, None), (I, None), (J, None), (K, None), (L, None), (M, None), (N, None), (O, None), (P, None), (Q, None), (R, None), (S, None), (T, None), (U, None), (V, None), (W, None), (X, None), (Y, None), (Z, None) ]
arcs: [ (, None)->i('A', {'B', 'Y'}), (, None)->i('A', {'B', 'Y'}), (, None)->i('C', {'Y'}), (, None)->i('D', {'Y'}), (, None)->i('H', {'Y'}), (, None)->i('I', {'I'}), (, None)->i('J', {'I'}), (, None)->i('L', {'L'}), (, None)->i('M', {'L'}), (, None)->i('O', {'L', 'X'}), (, None)->i('O', {'L', 'X'}), (, None)->i('Q', {'X'}), (, None)->i('R', {'I', 'R'}), (, None)->i('R', {'I', 'R'}), (, None)->i('S', {'R'}), (, None)->i('T', {'L', 'Y'}), (, None)->i('T', {'L', 'Y'}), (, None)->i('U', {'U'}), (, None)->i('U', {'Y'}), (, None)->i('V', {'V', 'X'}), (, None)->i('V', {'V', 'X'}), (, None)->i('W', {'L', 'W'}), (, None)->i('W', {'L', 'W'}), (, None)->i('Z', {'X'}), (A, None)->o, (B, None)->o('B', {'A'}), (C, None)->({'C'}, {'B'}), (D, None)->o, (E, None)->o, (F, None)->({'F'}, {'E'}), (G, None)->({'G'}, {'F'}), (H, None)->({'H'}, {'G'}), (I, None)->o('I', {'I'}), (I, None)->o('I', {'J', 'R'}), (J, None)->o, (K, None)->o, (L, None)->o('L', {'L', 'M', 'O', 'T'}), (L, None)->o('L', {'W'}), (M, None)->o, (N, None)->o, (O, None)->({'O'}, {'N'}), (P, None)->o, (Q, None)->({'Q'}, {'P'}), (R, None)->o('R', {'R'}), (R, None)->o('R', {'S'}), (S, None)->({'S'}, {'K'}), (T, None)->o, (U, None)->o, (U, None)->o('U', {'U'}), (V, None)->o, (V, None)->o('V', {'V'}), (W, None)->o, (W, None)->o('W', {'W'}), (X, None)->o('X', {'O', 'Q', 'V', 'Z'}), (Y, None)->o('Y', {'A'}), (Y, None)->o('Y', {'C', 'D', 'T', 'U'}), (Y, None)->o('Y', {'H'}), (Z, None)->({'Z'}, {'K'}), ({'C'}, {'B'})->(B, None), ({'F'}, {'E'})->(E, None), ({'G'}, {'F'})->(F, None), ({'H'}, {'G'})->(G, None), ({'O'}, {'N'})->(N, None), ({'Q'}, {'P'})->(P, None), ({'S'}, {'K'})->(K, None), ({'Z'}, {'K'})->(K, None), i('A', {'B', 'Y'})->(A, None), i('C', {'Y'})->(C, None), i('D', {'Y'})->(D, None), i('H', {'Y'})->(H, None), i('I', {'I'})->(I, None), i('J', {'I'})->(J, None), i('L', {'L'})->(L, None), i('M', {'L'})->(M, None), i('O', {'L', 'X'})->(O, None), i('Q', {'X'})->(Q, None), i('R', {'I', 'R'})->(R, None), i('S', {'R'})->(S, None), i('T', {'L', 'Y'})->(T, None), i('U', {'U'})->(U, None), i('U', {'Y'})->(U, None), i('V', {'V', 'X'})->(V, None), i('W', {'L', 'W'})->(W, None), i('Z', {'X'})->(Z, None), i->(I, None), i->(L, None), i->(X, None), i->(Y, None), o('B', {'A'})->(, None), o('I', {'I'})->(, None), o('I', {'J', 'R'})->(, None), o('I', {'J', 'R'})->(, None), o('L', {'L', 'M', 'O', 'T'})->(, None), o('L', {'L', 'M', 'O', 'T'})->(, None), o('L', {'L', 'M', 'O', 'T'})->(, None), o('L', {'L', 'M', 'O', 'T'})->(, None), o('L', {'W'})->(, None), o('R', {'R'})->(, None), o('R', {'S'})->(, None), o('U', {'U'})->(, None), o('V', {'V'})->(, None), o('W', {'W'})->(, None), o('X', {'O', 'Q', 'V', 'Z'})->(, None), o('X', {'O', 'Q', 'V', 'Z'})->(, None), o('X', {'O', 'Q', 'V', 'Z'})->(, None), o('X', {'O', 'Q', 'V', 'Z'})->(, None), o('Y', {'A'})->(, None), o('Y', {'C', 'D', 'T', 'U'})->(, None), o('Y', {'C', 'D', 'T', 'U'})->(, None), o('Y', {'C', 'D', 'T', 'U'})->(, None), o('Y', {'C', 'D', 'T', 'U'})->(, None), o('Y', {'H'})->(, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        def test_matrix2petrinet_mixed2(self):
                I = {
                        'A': [{'B'}, {'C'}],
                        'B': [{'Y'}],
                        'C': [{'C'}],
                        'D': [{'E'}, {'C'}],
                        'E': [{'F'}],
                        'F': [{'G'}],
                        'G': [{'N'}, {'H'}],
                        'H': [{'C'}],
                        'I': [{'W', 'I', 'K'}],
                        'J': [{'I'}],
                        'K': [{'X'}, {'K'}],
                        'L': [{'M', 'K'}],
                        'M': [{'K'}],
                        'N': [{'P', 'N'}],
                        'O': [{'N'}],
                        'P': [{'Q'}],
                        'Q': [{'K'}],
                        'R': [{'S'}],
                        'S': [{'K'}],
                        'T': [{'T'}, {'I'}],
                        'U': [{'T'}],
                        'V': [{'C'}],
                        'W': [{'W'}],
                        'X': [{'X'}],
                        'Y': [],
                        'Z': [{'E'}]
                }
                O = {
                        'B': [{'A'}],
                        'C': [{'D', 'A', 'H', 'V'}, {'C'}],
                        'Y': [{'B'}],
                        'E': [{'D', 'Z'}],
                        'F': [{'E'}],
                        'G': [{'F'}],
                        'H': [{'G'}],
                        'I': [{'J', 'I'}, {'T'}],
                        'K': [{'L'}, {'Q', 'S', 'M', 'I', 'K'}],
                        'M': [{'L'}],
                        'N': [{'O', 'N'}, {'G'}],
                        'Q': [{'P'}],
                        'S': [{'R'}],
                        'T': [{'T'}, {'U'}],
                        'W': [{'I'}, {'W'}],
                        'X': [{'X', 'K'}],
                        'A': [],
                        'D': [],
                        'V': [],
                        'L': [],
                        'P': [{'N'}],
                        'R': [],
                        'U': [],
                        'J': [],
                        'O': [],
                        'Z': []
                }
                transitions = list(set(I.keys()) & set(O.keys()))
                res,_,_ = self._subject(I, O, T=transitions)
#               self._visualise(res)
                cmp = """places: [ ({'B'}, {'A'}), ({'C'}, {'A', 'D', 'H', 'V'}), ({'C'}, {'C'}), ({'E'}, {'D', 'Z'}), ({'F'}, {'E'}), ({'G'}, {'F'}), ({'Q'}, {'P'}), ({'S'}, {'R'}), ({'Y'}, {'B'}), i, i('G', {'H'}), i('G', {'N'}), i('I', {'I', 'K', 'W'}), i('J', {'I'}), i('K', {'K'}), i('K', {'X'}), i('L', {'K', 'M'}), i('M', {'K'}), i('N', {'N', 'P'}), i('O', {'N'}), i('Q', {'K'}), i('S', {'K'}), i('T', {'I'}), i('T', {'T'}), i('U', {'T'}), i('W', {'W'}), i('X', {'X'}), o, o('H', {'G'}), o('I', {'I', 'J'}), o('I', {'T'}), o('K', {'I', 'K', 'M', 'Q', 'S'}), o('K', {'L'}), o('M', {'L'}), o('N', {'G'}), o('N', {'N', 'O'}), o('P', {'N'}), o('T', {'T'}), o('T', {'U'}), o('W', {'I'}), o('W', {'W'}), o('X', {'K', 'X'}) ]
transitions: [ (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (, None), (A, None), (B, None), (C, None), (D, None), (E, None), (F, None), (G, None), (H, None), (I, None), (J, None), (K, None), (L, None), (M, None), (N, None), (O, None), (P, None), (Q, None), (R, None), (S, None), (T, None), (U, None), (V, None), (W, None), (X, None), (Y, None), (Z, None) ]
arcs: [ (, None)->i('G', {'H'}), (, None)->i('G', {'N'}), (, None)->i('I', {'I', 'K', 'W'}), (, None)->i('I', {'I', 'K', 'W'}), (, None)->i('I', {'I', 'K', 'W'}), (, None)->i('J', {'I'}), (, None)->i('K', {'K'}), (, None)->i('K', {'X'}), (, None)->i('L', {'K', 'M'}), (, None)->i('L', {'K', 'M'}), (, None)->i('M', {'K'}), (, None)->i('N', {'N', 'P'}), (, None)->i('N', {'N', 'P'}), (, None)->i('O', {'N'}), (, None)->i('Q', {'K'}), (, None)->i('S', {'K'}), (, None)->i('T', {'I'}), (, None)->i('T', {'T'}), (, None)->i('U', {'T'}), (, None)->i('W', {'W'}), (, None)->i('X', {'X'}), (A, None)->o, (B, None)->({'B'}, {'A'}), (C, None)->({'C'}, {'A', 'D', 'H', 'V'}), (C, None)->({'C'}, {'C'}), (D, None)->o, (E, None)->({'E'}, {'D', 'Z'}), (F, None)->({'F'}, {'E'}), (G, None)->({'G'}, {'F'}), (H, None)->o('H', {'G'}), (I, None)->o('I', {'I', 'J'}), (I, None)->o('I', {'T'}), (J, None)->o, (K, None)->o('K', {'I', 'K', 'M', 'Q', 'S'}), (K, None)->o('K', {'L'}), (L, None)->o, (M, None)->o('M', {'L'}), (N, None)->o('N', {'G'}), (N, None)->o('N', {'N', 'O'}), (O, None)->o, (P, None)->o('P', {'N'}), (Q, None)->({'Q'}, {'P'}), (R, None)->o, (S, None)->({'S'}, {'R'}), (T, None)->o('T', {'T'}), (T, None)->o('T', {'U'}), (U, None)->o, (V, None)->o, (W, None)->o('W', {'I'}), (W, None)->o('W', {'W'}), (X, None)->o('X', {'K', 'X'}), (Y, None)->({'Y'}, {'B'}), (Z, None)->o, ({'B'}, {'A'})->(A, None), ({'C'}, {'A', 'D', 'H', 'V'})->(A, None), ({'C'}, {'A', 'D', 'H', 'V'})->(D, None), ({'C'}, {'A', 'D', 'H', 'V'})->(H, None), ({'C'}, {'A', 'D', 'H', 'V'})->(V, None), ({'C'}, {'C'})->(C, None), ({'E'}, {'D', 'Z'})->(D, None), ({'E'}, {'D', 'Z'})->(Z, None), ({'F'}, {'E'})->(E, None), ({'G'}, {'F'})->(F, None), ({'Q'}, {'P'})->(P, None), ({'S'}, {'R'})->(R, None), ({'Y'}, {'B'})->(B, None), i('G', {'H'})->(G, None), i('G', {'N'})->(G, None), i('I', {'I', 'K', 'W'})->(I, None), i('J', {'I'})->(J, None), i('K', {'K'})->(K, None), i('K', {'X'})->(K, None), i('L', {'K', 'M'})->(L, None), i('M', {'K'})->(M, None), i('N', {'N', 'P'})->(N, None), i('O', {'N'})->(O, None), i('Q', {'K'})->(Q, None), i('S', {'K'})->(S, None), i('T', {'I'})->(T, None), i('T', {'T'})->(T, None), i('U', {'T'})->(U, None), i('W', {'W'})->(W, None), i('X', {'X'})->(X, None), i->(C, None), i->(W, None), i->(X, None), i->(Y, None), o('H', {'G'})->(, None), o('I', {'I', 'J'})->(, None), o('I', {'I', 'J'})->(, None), o('I', {'T'})->(, None), o('K', {'I', 'K', 'M', 'Q', 'S'})->(, None), o('K', {'I', 'K', 'M', 'Q', 'S'})->(, None), o('K', {'I', 'K', 'M', 'Q', 'S'})->(, None), o('K', {'I', 'K', 'M', 'Q', 'S'})->(, None), o('K', {'I', 'K', 'M', 'Q', 'S'})->(, None), o('K', {'L'})->(, None), o('M', {'L'})->(, None), o('N', {'G'})->(, None), o('N', {'N', 'O'})->(, None), o('N', {'N', 'O'})->(, None), o('P', {'N'})->(, None), o('T', {'T'})->(, None), o('T', {'U'})->(, None), o('W', {'I'})->(, None), o('W', {'W'})->(, None), o('X', {'K', 'X'})->(, None), o('X', {'K', 'X'})->(, None) ]"""
                self.assertEqual(str(res), cmp, "Mismatching matrix and petri net")

        @staticmethod
        def _subject(I, O, T):
                # convert to indexable sets
                for t in T:
                        I[t] = [iset(s) for s in I[t]]
                        O[t] = [iset(s) for s in O[t]]
                return matrix2petrinet(GeneticMatrix(I, O, T))

        @staticmethod
        def _visualise(model, init = None, final = None, file = "test.png"):
                save_vis_petri_net(
                        model,
                        init or utils.initial_marking.discover_initial_marking(model),
                        final or utils.final_marking.discover_final_marking(model),
                        file_path = file,
                        debug = True
                )

if __name__ == '__main__':
        unittest.main()
