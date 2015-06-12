"""
Test harness for fitting the competing models.
"""
import time
import cPickle
import os
import gzip
import numpy as np

from collections import namedtuple

from pybasicbayes.util.text import progprint_xrange

# Use the Agg backend in running on a server without the DISPLAY variable
if "DISPLAY" not in os.environ:
    import matplotlib
    matplotlib.use('Agg')

from pyhawkes.utils.utils import convert_discrete_to_continuous
from pyhawkes.models import DiscreteTimeStandardHawkesModel, \
    DiscreteTimeNetworkHawkesModelGammaMixture, \
    DiscreteTimeNetworkHawkesModelGammaMixtureFixedSparsity, \
    DiscreteTimeNetworkHawkesModelSpikeAndSlab, \
    ContinuousTimeNetworkHawkesModel


Results = namedtuple("Results", ["samples", "timestamps", "lps", "test_lls"])

def fit_standard_hawkes_model_bfgs(S, S_test, dt, dt_max, output_path,
                                   standard_model=None,
                                   model_args={}, W_max=None):

    T,K = S.shape

    # Check for existing Gibbs results
    if os.path.exists(output_path):
        with gzip.open(output_path, 'r') as f:
            print "Loading Gibbs results from ", output_path
            results = cPickle.load(f)
    else:
        print "Fitting the data with a network Hawkes model using Gibbs sampling"

        test_model = DiscreteTimeStandardHawkesModel(K=K, dt=dt, dt_max=dt_max, W_max=W_max, **model_args)
        test_model.add_data(S)

        # Initialize the background rates to their mean
        test_model.initialize_to_background_rate()
        lps = [test_model.log_posterior()]
        hlls = [test_model.heldout_log_likelihood(S_test)]

        # Fit with BFGS
        tic = time.clock()
        test_model.fit_with_bfgs()
        init_time = time.clock() - tic

        lps.append(test_model.log_posterior())
        hlls.append(test_model.heldout_log_likelihood(S_test))

        # Convert to arrays
        lps = np.array(lps)
        hlls = np.array(hlls)
        timestamps = np.array([0, init_time])

        # Make results object
        results = Results([test_model.copy_sample()], timestamps, lps, hlls)

        # Save the model
        with gzip.open(output_path, 'w') as f:
            print "Saving BFGS results to ", output_path
            cPickle.dump(results, f, protocol=-1)

    return results

def fit_spikeslab_network_hawkes_gibbs(S, S_test, dt, dt_max, output_path,
                                       model_args={}, standard_model=None,
                                       N_samples=100):

    T,K = S.shape

    # Check for existing Gibbs results
    if os.path.exists(output_path):
        with gzip.open(output_path, 'r') as f:
            print "Loading Gibbs results from ", output_path
            results = cPickle.load(f)
    else:
        print "Fitting the data with a network Hawkes model using Gibbs sampling"

        test_model = DiscreteTimeNetworkHawkesModelSpikeAndSlab(K=K, dt=dt, dt_max=dt_max, **model_args)
        test_model.add_data(S)

        # Initialize with the standard model parameters
        if standard_model is not None:
            test_model.initialize_with_standard_model(standard_model)

        # TODO: Precompute F_test

        # Gibbs sample
        samples = []
        lps = [test_model.log_probability()]
        hlls = [test_model.heldout_log_likelihood(S_test)]
        times = [0]
        for _ in progprint_xrange(N_samples, perline=5):
            # Update the model
            tic = time.time()
            samples.append(test_model.resample_and_copy())
            times.append(time.time() - tic)

            # Compute log probability and heldout log likelihood
            lps.append(test_model.log_probability())
            hlls.append(test_model.heldout_log_likelihood(S_test))

            # # Save this sample
            # with open(output_path + ".gibbs.itr%04d.pkl" % itr, 'w') as f:
            #     cPickle.dump(samples[-1], f, protocol=-1)

        # Get cumulative timestamps
        timestamps = np.cumsum(times)
        lps = np.array(lps)
        hlls = np.array(hlls)

        # Make results object
        results = Results(samples, timestamps, lps, hlls)

        # Save the Gibbs samples
        with gzip.open(output_path, 'w') as f:
            print "Saving Gibbs samples to ", output_path
            cPickle.dump(results, f, protocol=-1)

    return results


def fit_ct_network_hawkes_gibbs(S, S_test, dt, dt_max, output_path,
                                model_args={}, standard_model=None,
                                N_samples=100):

    K = S.shape[1]
    S_ct, C_ct, T = convert_discrete_to_continuous(S, dt)
    S_test_ct, C_test_ct, T_test = convert_discrete_to_continuous(S_test, dt)

    # Check for existing Gibbs results
    if os.path.exists(output_path):
        with gzip.open(output_path, 'r') as f:
            print "Loading Gibbs results from ", output_path
            results = cPickle.load(f)
    else:
        print "Fitting the data with a network Hawkes model using Gibbs sampling"

        test_model = \
            ContinuousTimeNetworkHawkesModel(K, dt_max=dt_max, **model_args)
        test_model.add_data(S_ct, C_ct, T)

        # Initialize with the standard model parameters
        if standard_model is not None:
            test_model.initialize_with_standard_model(standard_model)

        # Gibbs sample
        samples = []
        lps = [test_model.log_probability()]
        hlls = [test_model.heldout_log_likelihood(S_test_ct, C_test_ct, T_test)]
        times = [0]
        for _ in progprint_xrange(N_samples, perline=5):
            # Update the model
            tic = time.time()
            samples.append(test_model.resample_and_copy())
            times.append(time.time() - tic)

            # Compute log probability and heldout log likelihood
            lps.append(test_model.log_probability())
            hlls.append(test_model.heldout_log_likelihood(S_test_ct, C_test_ct, T_test))

            # # Save this sample
            # with open(output_path + ".gibbs.itr%04d.pkl" % itr, 'w') as f:
            #     cPickle.dump(samples[-1], f, protocol=-1)

        # Get cumulative timestamps
        timestamps = np.cumsum(times)
        lps = np.array(lps)
        hlls = np.array(hlls)

        # Make results object
        results = Results(samples, timestamps, lps, hlls)

        # Save the Gibbs samples
        with gzip.open(output_path, 'w') as f:
            print "Saving Gibbs samples to ", output_path
            cPickle.dump(results, f, protocol=-1)

    return results

def fit_network_hawkes_vb(S, S_test, dt, dt_max, output_path,
                          model_args={}, standard_model=None,
                          N_samples=100):

    T,K = S.shape

    # Check for existing Gibbs results
    if os.path.exists(output_path):
        with gzip.open(output_path, 'r') as f:
            print "Loading VB results from ", output_path
            results = cPickle.load(f)
    else:
        print "Fitting the data with a network Hawkes model using batch VB"

        test_model = DiscreteTimeNetworkHawkesModelGammaMixtureFixedSparsity(K=K, dt=dt, dt_max=dt_max,
                                                                             **model_args)
        test_model.add_data(S)

        # Initialize with the standard model parameters
        if standard_model is not None:
            test_model.initialize_with_standard_model(standard_model)

        # TODO: Precompute F_test

        # Initialize with the standard model parameters
        if standard_model is not None:
            test_model.initialize_with_standard_model(standard_model)

        # Batch variational inference
        samples = []
        lps = [test_model.log_probability()]
        hlls = [test_model.heldout_log_likelihood(S_test)]
        times = [0]
        for itr in progprint_xrange(N_samples):
            # Update the model
            tic = time.time()
            test_model.meanfield_coordinate_descent_step()
            times.append(time.time() - tic)
            samples.append(test_model.copy_sample())

            # Resample from variational posterior to compute log prob and hlls
            test_model.resample_from_mf()

            # Compute log probability and heldout log likelihood
            lps.append(test_model.log_probability())
            hlls.append(test_model.heldout_log_likelihood(S_test))

            # Save this sample
            # with open(output_path + ".svi.itr%04d.pkl" % itr, 'w') as f:
            #     cPickle.dump(samples[-1], f, protocol=-1)

        # Get cumulative timestamps
        timestamps = np.cumsum(times)
        lps = np.array(lps)
        hlls = np.array(hlls)

        # Make results object
        results = Results(samples, timestamps, lps, hlls)

        # Save the Gibbs samples
        with gzip.open(output_path, 'w') as f:
            print "Saving VB samples to ", output_path
            cPickle.dump(results, f, protocol=-1)

    return results

def fit_network_hawkes_svi(S, S_test, dt, dt_max, output_path,
                           model_args={}, standard_model=None,
                           N_samples=100,
                           delay=10.0,
                           forgetting_rate=0.5):

    T,K = S.shape

    # Check for existing Gibbs results
    if os.path.exists(output_path):
        with gzip.open(output_path, 'r') as f:
            print "Loading SVI results from ", output_path
            results = cPickle.load(f)
    else:
        print "Fitting the data with a network Hawkes model using SVI"

        test_model = DiscreteTimeNetworkHawkesModelGammaMixtureFixedSparsity(K=K, dt=dt, dt_max=dt_max,
                                                                             **model_args)
        test_model.add_data(S)

        # Initialize with the standard model parameters
        if standard_model is not None:
            test_model.initialize_with_standard_model(standard_model)

        # TODO: Precompute F_test

        # Initialize with the standard model parameters
        if standard_model is not None:
            test_model.initialize_with_standard_model(standard_model)

        # TODO: Add the data in minibatches
        minibatchsize = 3000
        stepsize = (np.arange(N_samples) + delay)**(-forgetting_rate)

        # Stochastic variational inference
        samples = []
        lps = [test_model.log_probability()]
        hlls = [test_model.heldout_log_likelihood(S_test)]
        times = [0]
        for itr in progprint_xrange(N_samples):
            # Update the model
            tic = time.time()
            test_model.sgd_step(minibatchsize=minibatchsize, stepsize=stepsize[itr])
            times.append(time.time() - tic)
            samples.append(test_model.copy_sample())

            # Resample from variational posterior to compute log prob and hlls
            test_model.resample_from_mf()

            # Compute log probability and heldout log likelihood
            lps.append(test_model.log_probability())
            hlls.append(test_model.heldout_log_likelihood(S_test))

            # Save this sample
            # with open(output_path + ".svi.itr%04d.pkl" % itr, 'w') as f:
            #     cPickle.dump(samples[-1], f, protocol=-1)

        # Get cumulative timestamps
        timestamps = np.cumsum(times)
        lps = np.array(lps)
        hlls = np.array(hlls)

        # Make results object
        results = Results(samples, timestamps, lps, hlls)

        # Save the Gibbs samples
        with gzip.open(output_path, 'w') as f:
            print "Saving SVI samples to ", output_path
            cPickle.dump(results, f, protocol=-1)

    return results

def fit_poisson_glm():
    raise NotImplementedError