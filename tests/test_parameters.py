"""
Test and validate the creation of variational parameters and circuit parameters. 
"""
import unittest
import numpy as np
from scipy.fft import dst, dct

from openqaoa.qaoa_components import *
from openqaoa.utilities import X_mixer_hamiltonian, XY_mixer_hamiltonian
from openqaoa.qaoa_components.ansatz_constructor.gatemaplabel import GateMapType
from openqaoa.qaoa_components.variational_parameters.variational_params_factory import (
    PARAMS_CLASSES_MAPPER,
)

register = [0, 1, 2]
terms = [[0, 1], [2], [0, 2]]
weights = [1, 0.5, -2.0]

terms_wo_bias = [[0, 1], [1, 2]]
weights_wo_bias = [1, 0.5]

cost_hamiltonian = Hamiltonian.classical_hamiltonian(terms, weights, constant=0)
cost_hamiltonian_wo_bias = Hamiltonian.classical_hamiltonian(
    terms_wo_bias, weights_wo_bias, constant=0.7
)
mixer_hamiltonian = X_mixer_hamiltonian(len(register))


class TestingQAOADescriptor(unittest.TestCase):
    def setUp(self):

        self.p = 2
        self.cost_hamil = Hamiltonian(
            [
                PauliOp("ZZ", (0, 1)),
                PauliOp("ZZ", (1, 2)),
                PauliOp("ZZ", (0, 2)),
                PauliOp("Z", (0,)),
            ],
            [1, 1, 1, 0.5],
            1,
        )
        self.mixer_hamil = X_mixer_hamiltonian(n_qubits=3)
        self.mixer_gatemap = [RXGateMap(0), RXGateMap(1), RXGateMap(2)]
        self.mixer_gatemap_coeffs = self.mixer_hamil.coeffs

    def test_QAOADescriptor(self):

        """
        QAOADescriptor accept 2 types of inputs for mixer_blocks argument on initilisation. This test checks that the same mixer block when presented in Hamiltonian or as a List of RotationGateMap, plus the appropriate mixer coefficients, produces similar internal attributes.
        """

        qaoa_descriptor = QAOADescriptor(self.cost_hamil, self.mixer_hamil, p=self.p)

        qaoa_descriptor_gm = QAOADescriptor(
            self.cost_hamil,
            self.mixer_gatemap,
            p=self.p,
            mixer_coeffs=self.mixer_gatemap_coeffs,
        )

        # Check same number of mixer gates
        self.assertEqual(len(qaoa_descriptor.mixer_blocks), self.p)
        self.assertEqual(len(qaoa_descriptor_gm.mixer_blocks), self.p)
        for each_p_value in range(self.p):
            self.assertEqual(len(qaoa_descriptor.mixer_blocks[each_p_value]), 3)
            self.assertEqual(len(qaoa_descriptor_gm.mixer_blocks[each_p_value]), 3)
        # Check similar coefficients and qubit singles/pairs names
        self.assertEqual(
            qaoa_descriptor.mixer_single_qubit_coeffs,
            qaoa_descriptor_gm.mixer_single_qubit_coeffs,
        )
        self.assertEqual(
            qaoa_descriptor.mixer_pair_qubit_coeffs,
            qaoa_descriptor_gm.mixer_pair_qubit_coeffs,
        )
        self.assertEqual(
            qaoa_descriptor.mixer_qubits_singles,
            qaoa_descriptor_gm.mixer_qubits_singles,
        )
        self.assertEqual(
            qaoa_descriptor.mixer_qubits_pairs, qaoa_descriptor_gm.mixer_qubits_pairs
        )

    def test_QAOADescriptor_mixer_coeffs_selector_hamiltonian(self):

        """
        If a mixer hamiltonian is used for mixer_block, the coefficients will be obtained from it. Even if the user inputs his own mixer coefficient, it will be ignored.
        """

        verify_mixer_coeffs = [-1, -1, -1]

        mixer_hamil = X_mixer_hamiltonian(n_qubits=3)

        qaoa_descriptor = QAOADescriptor(self.cost_hamil, self.mixer_hamil, p=self.p)
        qaoa_descriptor_2 = QAOADescriptor(
            self.cost_hamil, self.mixer_hamil, p=self.p, mixer_coeffs=[1, 0, 1]
        )

        self.assertEqual(qaoa_descriptor.mixer_block_coeffs, verify_mixer_coeffs)
        self.assertEqual(qaoa_descriptor_2.mixer_block_coeffs, verify_mixer_coeffs)

    def test_QAOADescriptor_mixer_coeffs_selector_gatemap(self):

        """
        If a mixer gatemap is used for mixer_block, the user is required to input his own mixer coefficients, there should be an error message if the user does not input the appropriate number of mixer coefficients.
        """

        verify_mixer_coeffs = [-1, -1, -1]

        qaoa_descriptor = QAOADescriptor(
            self.cost_hamil,
            self.mixer_gatemap,
            p=self.p,
            mixer_coeffs=self.mixer_gatemap_coeffs,
        )

        self.assertEqual(qaoa_descriptor.mixer_block_coeffs, verify_mixer_coeffs)

        with self.assertRaises(ValueError) as cm:
            QAOADescriptor(self.cost_hamil, self.mixer_gatemap, self.p, [])
            self.assertEqual(
                "The number of terms/gatemaps must match the number of coefficients provided.",
                str(cm.exception),
            )

    def test_QAOADescriptor_assign_coefficients(self):

        """
        The method should split the coefficients and gatemaps in the proper order. Regardless of their positions within the hamiltonian or gatemap list.
        """

        verify_mixer_coeffs = [-1, -1, -1, -0.5]

        # TestCase 1: GateMap Mixer
        mixer_gatemap = [RXGateMap(0), RXGateMap(1), RXGateMap(2), RXXGateMap(0, 2)]

        qaoa_descriptor = QAOADescriptor(
            self.cost_hamil, mixer_gatemap, p=self.p, mixer_coeffs=[-1, -1, -1, -0.5]
        )

        self.assertEqual(qaoa_descriptor.cost_single_qubit_coeffs, [0.5])
        self.assertEqual(qaoa_descriptor.cost_pair_qubit_coeffs, [1, 1, 1])
        self.assertEqual(qaoa_descriptor.cost_qubits_singles, ["RZGateMap"])
        self.assertEqual(
            qaoa_descriptor.cost_qubits_pairs,
            ["RZZGateMap", "RZZGateMap", "RZZGateMap"],
        )

        self.assertEqual(qaoa_descriptor.mixer_single_qubit_coeffs, [-1, -1, -1])
        self.assertEqual(qaoa_descriptor.mixer_pair_qubit_coeffs, [-0.5])
        self.assertEqual(
            qaoa_descriptor.mixer_qubits_singles,
            ["RXGateMap", "RXGateMap", "RXGateMap"],
        )
        self.assertEqual(qaoa_descriptor.mixer_qubits_pairs, ["RXXGateMap"])

        # TestCase 2: Hamiltonian Mixer
        mixer_gatemap = XY_mixer_hamiltonian(n_qubits=3)

        qaoa_descriptor = QAOADescriptor(self.cost_hamil, mixer_gatemap, p=self.p)

        self.assertEqual(qaoa_descriptor.cost_single_qubit_coeffs, [0.5])
        self.assertEqual(qaoa_descriptor.cost_pair_qubit_coeffs, [1, 1, 1])
        self.assertEqual(qaoa_descriptor.cost_qubits_singles, ["RZGateMap"])
        self.assertEqual(
            qaoa_descriptor.cost_qubits_pairs,
            ["RZZGateMap", "RZZGateMap", "RZZGateMap"],
        )

        self.assertEqual(qaoa_descriptor.mixer_single_qubit_coeffs, [])
        self.assertEqual(
            qaoa_descriptor.mixer_pair_qubit_coeffs, [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        )
        self.assertEqual(qaoa_descriptor.mixer_qubits_singles, [])
        self.assertEqual(
            qaoa_descriptor.mixer_qubits_pairs,
            [
                "RXXGateMap",
                "RYYGateMap",
                "RXXGateMap",
                "RYYGateMap",
                "RXXGateMap",
                "RYYGateMap",
            ],
        )

    def test_QAOADescriptor_cost_blocks(self):

        """
        cost_blocks property should always return a list of RotationGateMaps based on the input cost hamiltonian.
        """

        mixer_gatemap = [RXGateMap(0), RXGateMap(1), RXGateMap(2), RXXGateMap(0, 2)]

        qaoa_descriptor = QAOADescriptor(
            self.cost_hamil, mixer_gatemap, p=self.p, mixer_coeffs=[-1, -1, -1, -0.5]
        )

        for p_index, each_p_block in enumerate(qaoa_descriptor.cost_blocks):
            for each_item in each_p_block:
                self.assertTrue(isinstance(each_item, RotationGateMap))
                self.assertEqual(each_item.gate_label.type, GateMapType.COST)
                self.assertEqual(each_item.gate_label.layer, p_index)

            self.assertEqual(
                [each_item.gate_label.sequence for each_item in each_p_block],
                [0, 1, 2, 0],
            )

    def test_QAOADescriptor_mixer_blocks(self):

        """
        mixer_blocks property should always return a list of RotationGateMaps based on the input cost hamiltonian.
        """

        mixer_gatemap = [RXGateMap(0), RXGateMap(1), RXGateMap(2), RXXGateMap(0, 2)]

        qaoa_descriptor = QAOADescriptor(
            self.cost_hamil, mixer_gatemap, p=self.p, mixer_coeffs=[-1, -1, -1, -0.5]
        )

        for p_index, each_p_block in enumerate(qaoa_descriptor.mixer_blocks):
            for each_item in each_p_block:
                self.assertTrue(isinstance(each_item, RotationGateMap))
                self.assertEqual(each_item.gate_label.type, GateMapType.MIXER)
                self.assertEqual(each_item.gate_label.layer, p_index)

            self.assertEqual(
                [each_item.gate_label.sequence for each_item in each_p_block],
                [0, 1, 2, 0],
            )

    def test_QAOADescriptor_weird_cases(self):

        """
        Testing various weird cases
        """

        # TestCase 1: Empty List Mixer Block
        qaoa_descriptor = QAOADescriptor(self.cost_hamil, [], p=self.p)

        # TestCase 2: Wrong Type Cost Block
        self.assertRaises(AttributeError, QAOADescriptor, [], self.mixer_hamil, self.p)
        self.assertRaises(
            AttributeError, QAOADescriptor, [RZGateMap(0)], self.mixer_hamil, self.p
        )

        # TestCase 3: p is not an int
        self.assertRaises(
            TypeError, QAOADescriptor, self.cost_hamil, self.mixer_hamil, "test"
        )

    def test_QAOADescriptor_abstract_circuit(self):

        """
        The abstract circuit should be consistent with the cost hamiltonian, mixer block and the p value.
        """

        mixer_hamil = X_mixer_hamiltonian(n_qubits=3)
        mixer_gatemap = [RXGateMap(0), RXGateMap(1), RXGateMap(2)]

        qaoa_descriptor = QAOADescriptor(self.cost_hamil, self.mixer_hamil, p=self.p)
        qaoa_descriptor_gm = QAOADescriptor(
            self.cost_hamil,
            self.mixer_gatemap,
            p=self.p,
            mixer_coeffs=self.mixer_gatemap_coeffs,
        )

        # Checks if the gates are identical
        for each_cp_gate, each_cpgm_gate in zip(
            qaoa_descriptor.abstract_circuit, qaoa_descriptor_gm.abstract_circuit
        ):
            self.assertTrue(type(each_cp_gate), type(each_cpgm_gate))
            if hasattr(each_cp_gate, "qubit_1"):
                self.assertEqual(each_cp_gate.qubit_1, each_cpgm_gate.qubit_1)
            if hasattr(each_cpgm_gate, "qubit_2"):
                self.assertEqual(each_cp_gate.qubit_2, each_cpgm_gate.qubit_2)


class TestingQAOAVariationalParameters(unittest.TestCase):
    def test_QAOAVariationalExtendedParams(self):
        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        params = QAOAVariationalExtendedParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, time=2
        )

        assert np.allclose(qaoa_descriptor.qureg, [0, 1, 2])
        assert np.allclose(params.betas_singles, [[0.75] * 3, [0.25] * 3])
        assert np.allclose(params.betas_pairs, [])
        assert np.allclose(params.gammas_singles, [[0.25], [0.75]])
        assert np.allclose(params.gammas_pairs, [[0.25, 0.25], [0.75, 0.75]])
        # Test updating and raw output
        raw = np.random.rand(len(params))
        params.update_from_raw(raw)
        assert np.allclose(raw, params.raw())

    # TODO check that the values also make sense
    def test_QAOAVariationalExtendedParamsCustomInitialisation(self):
        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)

        betas_singles = [[0.0, 0.1, 0.3], [0.5, 0.2, 1.2]]
        betas_pairs = []
        gammas_singles = [[0.0], [0.5]]
        gammas_pairs = [[0.1, 0.3], [0.2, 1.2]]
        params = QAOAVariationalExtendedParams(
            qaoa_descriptor, betas_singles, betas_pairs, gammas_singles, gammas_pairs
        )

        cost_2q_angles = 2 * np.array([1, -2.0]) * gammas_pairs
        cost_1q_angles = 2 * np.array([0.5]) * gammas_singles
        mixer_1q_angles = 2 * np.array([-1, -1, -1]) * betas_singles
        mixer_2q_angles = []

        assert np.allclose(params.betas_singles, betas_singles)
        assert np.allclose(params.betas_pairs, betas_pairs)
        assert np.allclose(params.gammas_singles, gammas_singles)
        assert np.allclose(params.gammas_pairs, gammas_pairs)

        assert np.allclose(params.mixer_1q_angles, mixer_1q_angles)
        assert np.allclose(params.mixer_2q_angles, mixer_2q_angles)
        assert np.allclose(params.cost_1q_angles, cost_1q_angles)
        assert np.allclose(params.cost_2q_angles, cost_2q_angles)

    def test_QAOAVariationalStandardWithBiasParamsCustomInitialisation(self):
        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)

        betas = [np.pi, 0.4]
        gammas_singles = [10, 24]
        gammas_pairs = [8.8, 2.3]
        params = QAOAVariationalStandardWithBiasParams(
            qaoa_descriptor, betas, gammas_singles, gammas_pairs
        )

        cost_2q_angles = 2 * np.outer(gammas_pairs, np.array([1, -2.0]))
        cost_1q_angles = 2 * np.outer(gammas_singles, np.array([0.5]))
        mixer_1q_angles = 2 * np.outer(betas, np.array([-1, -1, -1]))
        mixer_2q_angles = []

        assert np.allclose(params.betas, betas)
        assert np.allclose(params.gammas_singles, gammas_singles)
        assert np.allclose(params.gammas_pairs, gammas_pairs)

        assert np.allclose(params.mixer_1q_angles, mixer_1q_angles)
        assert np.allclose(params.mixer_2q_angles, mixer_2q_angles)
        assert np.allclose(params.cost_1q_angles, cost_1q_angles)
        assert np.allclose(params.cost_2q_angles, cost_2q_angles)
        assert type(params) == QAOAVariationalStandardWithBiasParams

    def test_QAOAVariationalAnnealingParamsCustomInitialisation(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        schedule = [0.4, 1.0]
        annealing_params = QAOAVariationalAnnealingParams(
            qaoa_descriptor, total_annealing_time=5, schedule=schedule
        )

        assert type(annealing_params) == QAOAVariationalAnnealingParams

    def test_QAOAVariationalFourierParamsCustomInitialisation(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        v = [0.4, 1.0]
        u = [0.5, 1.2]
        fourier_params = QAOAVariationalFourierParams(qaoa_descriptor, q=2, v=v, u=u)

        assert np.allclose(fourier_params.betas, dct(v, n=qaoa_descriptor.p, axis=0))
        assert np.allclose(fourier_params.gammas, dst(u, n=qaoa_descriptor.p, axis=0))
        assert type(fourier_params) == QAOAVariationalFourierParams

    def test_QAOAVariationalFourierExtendedParamsCustomInitialisation(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        v_singles = [[0.4] * 3, [1.0] * 3]
        v_pairs = []
        u_singles = [[0.5], [1.2]]
        u_pairs = [[4.5] * 2, [123] * 2]
        fourier_params = QAOAVariationalFourierExtendedParams(
            qaoa_descriptor, 2, v_singles, v_pairs, u_singles, u_pairs
        )

        assert np.allclose(
            fourier_params.betas_singles, dct(v_singles, n=qaoa_descriptor.p, axis=0)
        )
        assert np.allclose(
            fourier_params.gammas_singles, dst(u_singles, n=qaoa_descriptor.p, axis=0)
        )
        assert np.allclose(
            fourier_params.gammas_pairs, dst(u_pairs, n=qaoa_descriptor.p, axis=0)
        )

        assert type(fourier_params) == QAOAVariationalFourierExtendedParams

    def test_QAOAVariationalAnnealingParams(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        params = QAOAVariationalAnnealingParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, total_annealing_time=2
        )

        assert np.allclose(qaoa_descriptor.qureg, [0, 1, 2])
        assert np.allclose(params.mixer_1q_angles, [[-2 * 0.75] * 3, [-2 * 0.25] * 3])
        assert np.allclose(params.cost_1q_angles, [[2 * 0.125], [2 * 0.375]])
        assert np.allclose(
            params.cost_2q_angles, [[2 * 0.25, -0.5 * 2], [2 * 0.75, -1.5 * 2]]
        )

        # Test updating and raw output
        raw = np.random.rand(len(params))
        params.update_from_raw(raw)
        assert np.allclose(raw, params.raw())

    def test_QAOAVariationalStandardWithBiasParams(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        params = QAOAVariationalStandardWithBiasParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, time=2
        )
        assert np.allclose(qaoa_descriptor.qureg, [0, 1, 2])
        assert np.allclose(params.mixer_1q_angles, [[-2 * 0.75] * 3, [-2 * 0.25] * 3])
        assert np.allclose(params.cost_1q_angles, [[2 * 0.125], [2 * 0.375]])
        assert np.allclose(
            params.cost_2q_angles, [[2 * 0.25, -0.5 * 2], [2 * 0.75, -1.5 * 2]]
        )

        # Test updating and raw output
        raw = np.random.rand(len(params))
        params.update_from_raw(raw)
        assert np.allclose(raw, params.raw())

    def test_QAOAVariationalStandardParams(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        params = QAOAVariationalStandardParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, time=2
        )

        assert np.allclose(qaoa_descriptor.qureg, [0, 1, 2])
        assert np.allclose(params.mixer_1q_angles, [[-2 * 0.75] * 3, [-2 * 0.25] * 3])
        assert np.allclose(params.cost_1q_angles, [[2 * 0.125], [2 * 0.375]])
        assert np.allclose(
            params.cost_2q_angles, [[2 * 0.25, -0.5 * 2], [2 * 0.75, -1.5 * 2]]
        )

        # Test updating and raw output
        raw = np.random.rand(len(params))
        params.update_from_raw(raw)
        assert np.allclose(raw, params.raw())

    def test_non_fourier_params_are_consistent(self):
        """
        Check that StandardParams, StandardWithBiasParams and
        ExtendedParams give the same rotation angles, given the same data"""
        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)
        p1 = QAOAVariationalStandardParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, time=2
        )
        p2 = QAOAVariationalExtendedParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, time=2
        )
        p3 = QAOAVariationalStandardWithBiasParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, time=2
        )

        assert np.allclose(p1.mixer_1q_angles, p2.mixer_1q_angles)
        assert np.allclose(p2.mixer_1q_angles, p3.mixer_1q_angles)
        assert np.allclose(p1.cost_1q_angles, p2.cost_1q_angles)
        assert np.allclose(p2.cost_1q_angles, p3.cost_1q_angles)
        assert np.allclose(p1.cost_2q_angles, p2.cost_2q_angles)
        assert np.allclose(p2.cost_2q_angles, p3.cost_2q_angles)

    def test_QAOAVariationalFourierParams(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=3)
        params = QAOAVariationalFourierParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, q=2, time=2
        )

        # just access the angles, to check that it actually creates them
        assert len(params.cost_1q_angles) == len(params.cost_2q_angles)
        assert np.allclose(params.v, [1 / 3, 0])
        assert np.allclose(params.u, [1 / 3, 0])
        # Test updating and raw output
        raw = np.random.rand(len(params))
        params.update_from_raw(raw)
        assert np.allclose(raw, params.raw())

    def test_QAOAVariationalFourierWithBiasParams(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=3)
        params = QAOAVariationalFourierWithBiasParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, q=2, time=2
        )

        # just access the angles, to check that it actually creates them
        assert len(params.cost_1q_angles) == len(params.cost_2q_angles)
        assert np.allclose(params.v, [1 / 3, 0])
        assert np.allclose(params.u_singles, [1 / 3, 0])
        assert np.allclose(params.u_pairs, [1 / 3, 0])
        # Test updating and raw output
        raw = np.random.rand(len(params))
        params.update_from_raw(raw)
        assert np.allclose(raw, params.raw())

    def test_QAOAVariationalFourierExtendedParams(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=3)
        params = QAOAVariationalFourierExtendedParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, q=2, time=2
        )

        # just access the angles, to check that it actually creates them
        assert len(params.cost_1q_angles) == len(params.cost_2q_angles)
        # Test updating and raw output

        assert np.allclose(params.v_singles, [[1 / 3] * 3, [0] * 3])
        assert np.allclose(params.u_singles, [[1 / 3] * 1, [0] * 1])
        assert np.allclose(params.u_pairs, [[1 / 3] * 2, [0] * 2])
        # Test updating and raw output
        raw = np.random.rand(len(params))
        params.update_from_raw(raw)
        assert np.allclose(raw, params.raw())

    def test_FourierParams_are_consistent(self):
        """
        Check, that both Fourier Parametrizations give the same rotation angles,
        given the same data"""
        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=3)

        params1 = QAOAVariationalFourierParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, q=2, time=2
        )
        params2 = QAOAVariationalFourierWithBiasParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, q=2, time=2
        )
        params3 = QAOAVariationalFourierExtendedParams.linear_ramp_from_hamiltonian(
            qaoa_descriptor, q=2, time=2
        )

        assert np.allclose(params1.mixer_1q_angles, params2.mixer_1q_angles)
        assert np.allclose(params1.cost_1q_angles, params2.cost_1q_angles)
        assert np.allclose(params1.cost_2q_angles, params2.cost_2q_angles)
        assert np.allclose(params1.mixer_1q_angles, params3.mixer_1q_angles)
        assert np.allclose(params1.cost_1q_angles, params3.cost_1q_angles)
        assert np.allclose(params1.cost_2q_angles, params3.cost_2q_angles)

    def test_inputChecking(self):

        # Check that an error is raised if we pass in an extra angle in `betas` (depth is 3, here we give 4 beta values)
        reg = [0, 1]
        terms = [[0, 1]]
        weights = [0.7]
        n_layers = 3
        betas_singles = [1, 2, 3, 4]
        betas_pairs = []
        gammas_singles = []
        gammas_pairs = [1, 2, 3]
        qaoa_descriptor = QAOADescriptor(
            cost_hamiltonian, mixer_hamiltonian, p=n_layers
        )
        self.assertRaises(
            ValueError,
            QAOAVariationalExtendedParams,
            qaoa_descriptor,
            betas_singles,
            betas_pairs,
            gammas_singles,
            gammas_pairs,
        )

    def test_str_and_repr(self):

        qaoa_descriptor = QAOADescriptor(cost_hamiltonian, mixer_hamiltonian, p=2)

        for each_key_value in PARAMS_CLASSES_MAPPER.keys():
            variate_params = create_qaoa_variational_params(
                qaoa_descriptor,
                params_type=each_key_value,
                init_type="rand",
                q=1,
                total_annealing_time=1,
            )

            self.assertEqual(variate_params.__str__(), variate_params.__repr__())

    # # Plot Tests

    # def test_StandardParams_plot(self):

    #     register_wo_bias = [0, 1, 2]
    #     terms_wo_bias = [[0, 1], [0, 2]]
    #     weights_wo_bias = [1, -2.0]

    #     p = 5
    #     hyperparams = HyperParams(terms,weights,register,p)
    #     params = StandardParams.linear_ramp_from_hamiltonian(hyperparams)
    #     fig, ax = plt.subplots()
    #     params.plot(ax=ax)
    #     # plt.show()

    #     p = 8
    #     hyperparams = HyperParams(terms,weights,register,p)
    #     params = StandardParams(hyperparams,([0.1]*p, [0.2]*p))
    #     fig, ax = plt.subplots()
    #     params.plot(ax=ax)
    #     # plt.show()

    #     p = 2
    #     hyperparams = HyperParams(terms_wo_bias,weights_wo_bias,register_wo_bias,p)
    #     params = StandardParams(hyperparams,([5]*p, [10]*p))
    #     fig, ax = plt.subplots()
    #     params.plot(ax=ax)
    #     # plt.show()

    # def test_ExtendedParams_plot(self):

    #     register_wo_bias = [0, 1, 2]
    #     terms_wo_bias = [[0, 1], [0, 2]]
    #     weights_wo_bias = [1, -2.0]

    #     p = 5
    #     hyperparams = HyperParams(terms_wo_bias,weights_wo_bias,register_wo_bias,p)
    #     params = ExtendedParams.linear_ramp_from_hamiltonian(hyperparams, p)
    #     fig, ax = plt.subplots()
    #     params.plot(ax=ax)
    #     # plt.show()

    #     p = 8
    #     hyperparams = HyperParams(terms_wo_bias,weights_wo_bias,register_wo_bias,p)
    #     params = ExtendedParams(hyperparams,
    #                             ([0.1] * p*len(register),
    #                             [],
    #                             [0.2] * p*len(weights_wo_bias)))
    #     fig, ax = plt.subplots()
    #     params.plot(ax=ax)
    #     # plt.show()

    # def test_extended_get_constraints(self):
    #     register = [0,1,2,3]
    #     terms = [[0, 1], [1, 2], [2, 3], [3, 0]]
    #     weights = [0.1, 0.3, 0.5, -0.7]
    #     p = 2

    #     hyperparams = HyperParams(terms,weights,register,p)
    #     params = ExtendedParams.linear_ramp_from_hamiltonian(hyperparams)

    #     actual_constraints = params.get_constraints()

    #     expected_constraints = [(0, 2 * np.pi), (0, 2 * np.pi),
    #                             (0, 2 * np.pi), (0, 2 * np.pi),
    #                             (0, 2 * np.pi), (0, 2 * np.pi),
    #                             (0, 2 * np.pi), (0, 2 * np.pi),
    #                             (0, 2 * np.pi / weights[0]),
    #                             (0, 2 * np.pi / weights[1]),
    #                             (0, 2 * np.pi / weights[2]),
    #                             (0, 2 * np.pi / weights[3]),
    #                             (0, 2 * np.pi / weights[0]),
    #                             (0, 2 * np.pi / weights[1]),
    #                             (0, 2 * np.pi / weights[2]),
    #                             (0, 2 * np.pi / weights[3])]

    #     assert(np.allclose(expected_constraints, actual_constraints))

    #     cost_function = QAOACostVector(params)
    #     np.random.seed(0)
    #     random_angles = np.random.uniform(-100, 100, size=len(params.raw()))
    #     value = cost_function(random_angles)

    #     normalised_angles = [random_angles[i] % actual_constraints[i][1]
    #                         for i in range(len(params.raw()))]
    #     normalised_value = cost_function(normalised_angles)

    #     assert(np.allclose(value, normalised_value))


if __name__ == "__main__":
    unittest.main()
