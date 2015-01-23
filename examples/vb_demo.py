import numpy as np
import matplotlib.pyplot as plt

from pyhawkes.models import DiscreteTimeNetworkHawkesModelMeanField, DiscreteTimeNetworkHawkesModelGibbs

def demo(seed=None):
    """
    Create a discrete time Hawkes model and generate from it.

    :return:
    """
    if seed is None:
        seed = np.random.randint(2**32)

    print "Setting seed to ", seed
    np.random.seed(seed)


    K = 20
    T = 1000
    dt = 1.0
    B = 3

    # Generate from a true model
    true_model = DiscreteTimeNetworkHawkesModelGibbs(K=K, dt=dt, B=B, p=0.5, v=K)
    # true_model.resample_from_mf()
    S,R = true_model.generate(T=T)

    # Make a new model for inference
    model = DiscreteTimeNetworkHawkesModelMeanField(K=K, dt=dt, B=B, p=0.5, v=K)
    model.resample_from_mf()
    model.add_data(S)

    # Plot the true and inferred firing rate
    plt.figure()
    plt.plot(np.arange(T), R[:,1], '-k', lw=2)
    plt.ion()
    ln = plt.plot(np.arange(T), model.compute_rate()[:,1], '-r')[0]
    plt.show()

    # Gibbs sample
    N_iters = 1000
    vlbs = []
    for itr in xrange(N_iters):
        vlbs.append(model.meanfield_coordinate_descent_step())

        if itr > 0:
            if (vlbs[-2] - vlbs[-1]) > 1e-1:
                import pdb; pdb.set_trace()
                raise Exception("VLB is not increasing!")

        # Resample from variational distribution and plot
        model.resample_from_mf()

        # Update plot
        if itr % 5 == 0:
            ln.set_data(np.arange(T), model.compute_rate()[:,1])
            plt.title("Iteration %d" % itr)
            plt.pause(0.001)

    plt.ioff()

    print "A true:        ", true_model.weight_model.A
    print "W true:        ", true_model.weight_model.W
    print "g true:         ", true_model.impulse_model.g
    print "lambda0 true:  ", true_model.bias_model.lambda0
    print ""
    print "A mean:        ", model.weight_model.expected_A()
    print "W mean:        ", model.weight_model.expected_W()
    print "g mean:        ", model.impulse_model.expected_g()
    print "lambda0 mean:  ", model.bias_model.expected_lambda0()

    plt.figure()
    plt.plot(np.arange(N_iters), vlbs)
    plt.xlabel("Iteration")
    plt.ylabel("VLB")
    plt.show()

demo(1689018265)