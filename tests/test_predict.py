# Copyright 2016 the GPflow authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import numpy as np
import pytest

import gpflow
from gpflow.features import InducingPoints
from gpflow.kernels import Matern32

rng = np.random.RandomState(0)


@pytest.mark.parametrize('Ntrain, Ntest, D', [[100, 10, 2]])
def test_gaussian_mean_and_variance(Ntrain, Ntest, D):
    X, Y = rng.randn(Ntrain, D), rng.randn(Ntrain, 1)
    Xtest, _ = rng.randn(Ntest, D), rng.randn(Ntest, 1)
    kern = Matern32() + gpflow.kernels.White()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    mu_f, var_f = model_gp.predict_f(Xtest)
    mu_y, var_y = model_gp.predict_y(Xtest)

    assert np.allclose(mu_f, mu_y)
    assert np.allclose(var_f, var_y - 1.)


@pytest.mark.parametrize('Ntrain, Ntest, D', [[100, 10, 2]])
def test_gaussian_log_density(Ntrain, Ntest, D):
    X, Y = rng.randn(Ntrain, D), rng.randn(Ntrain, 1)
    Xtest, Ytest = rng.randn(Ntest, D), rng.randn(Ntest, 1)
    kern = Matern32() + gpflow.kernels.White()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    mu_y, var_y = model_gp.predict_y(Xtest)
    log_density = model_gp.predict_log_density(Xtest, Ytest)
    log_density_hand = (-0.5 * np.log(2 * np.pi) -
                        0.5 * np.log(var_y) -
                        0.5 * np.square(mu_y - Ytest) / var_y)

    assert np.allclose(log_density_hand, log_density)


@pytest.mark.parametrize('input_dim, output_dim, N, Ntest, M', [
    [3, 2, 20, 30, 5]
])
def test_gaussian_full_cov(input_dim, output_dim, N, Ntest, M):
    covar_shape = (output_dim, Ntest, Ntest)
    X, Y, Z = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    Xtest = rng.randn(Ntest, input_dim)
    kern = Matern32()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    mu1, var = model_gp.predict_f(Xtest, full_cov=False)
    mu2, covar = model_gp.predict_f(Xtest, full_cov=True)

    assert np.allclose(mu1, mu2, atol=1.e-10)
    assert covar.shape == covar_shape
    assert var.shape == (Ntest, output_dim)
    for i in range(output_dim):
        assert np.allclose(var[:, i], np.diag(covar[i, :, :]))


# TODO(@sergio.pasc) As model classes are updated to TF2.0, prepare all tests bellow accordingly

@pytest.mark.skip(reason='GPR model is not ready')
@pytest.mark.parametrize('input_dim, output_dim, N, Ntest, M, num_samples', [
    [3, 2, 20, 30, 5, 5]
])
def test_gaussian_full_cov_samples(input_dim, output_dim, N, Ntest, M, num_samples):
    samples_shape = (num_samples, Ntest, output_dim)
    X, Y, _ = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    Xtest = rng.randn(Ntest, input_dim)
    kern = Matern32()
    model_gp = gpflow.models.GPR(X, Y, kernel=kern)

    samples = model_gp.predict_f_samples(Xtest, num_samples)
    assert samples.shape == samples_shape


class ModelSetup:
    def __init__(self, model_class, kernel=Matern32(), likelihood=gpflow.likelihoods.Gaussian(),
                 whiten=None, q_diag=None, requires_Z_as_input=True):
        self.model_class = model_class
        self.kernel = kernel
        self.likelihood = likelihood
        self.whiten = whiten
        self.q_diag = q_diag
        self.requires_Z_as_input = requires_Z_as_input

    def get_model(self, Z):
        if self.whiten is not None and self.q_diag is not None:
            return self.model_class(feature=Z, kernel=self.kernel, likelihood=self.likelihood,
                                    whiten=self.whiten, q_diag=self.q_diag)
        else:
            return self.model_class(feature=Z, kernel=self.kernel, likelihood=self.likelihood)


model_setups = [
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=False, q_diag=True),
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=True, q_diag=False),
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=True, q_diag=True),
    ModelSetup(model_class=gpflow.models.SVGP,
               whiten=False, q_diag=False),
    #     ModelSetup(model_class=gpflow.models.SGPR),
    #     ModelSetup(model_class=gpflow.models.GPRF),
    #     ModelSetup(model_class=gpflow.models.VGP, requires_Z_as_input = False),
    #     ModelSetup(model_class=gpflow.models.GPMC, requires_Z_as_input = False ),
    #     ModelSetup(model_class=gpflow.models.SGPMC)
]


@pytest.mark.parametrize('model_setup', model_setups)
@pytest.mark.parametrize('input_dim', [3])
@pytest.mark.parametrize('output_dim', [2])
@pytest.mark.parametrize('N', [20])
@pytest.mark.parametrize('Ntest', [30])
@pytest.mark.parametrize('M', [5])
def test_other_models_full_cov(model_setup, input_dim, output_dim, N, Ntest, M):
    covar_shape = (output_dim, Ntest, Ntest)
    # TODO(@awav): may need them for other models
    # X, Y = rng.randn(N, input_dim), rng.randn(N, output_dim)
    Z = InducingPoints(rng.randn(M, input_dim))
    Xtest = rng.randn(Ntest, input_dim)
    model_gp = model_setup.get_model(Z)

    mu1, var = model_gp.predict_f(Xtest, full_cov=False)
    mu2, covar = model_gp.predict_f(Xtest, full_cov=True)

    assert np.allclose(mu1, mu2, atol=1.e-10)
    assert covar.shape == covar_shape
    assert var.shape == (Ntest, output_dim)
    for i in range(output_dim):
        assert np.allclose(var[:, i], np.diag(covar[i, :, :]))


@pytest.mark.parametrize('model_setup', model_setups)
@pytest.mark.parametrize('input_dim', [3])
@pytest.mark.parametrize('output_dim', [2])
@pytest.mark.parametrize('N', [20])
@pytest.mark.parametrize('Ntest', [30])
@pytest.mark.parametrize('M', [5])
@pytest.mark.parametrize('num_samples', [5])
def test_other_models_full_cov_samples(model_setup, input_dim, output_dim, N, Ntest, M,
                                       num_samples):
    samples_shape = (num_samples, Ntest, output_dim)
    # TODO(@awav): may need them for other models
    # X, Y, Z = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    _, _, Z = rng.randn(N, input_dim), rng.randn(N, output_dim), rng.randn(M, input_dim)
    Xtest = rng.randn(Ntest, input_dim)
    model_gp = model_setup.get_model(Z)

    samples = model_gp.predict_f_samples(Xtest, num_samples)
    assert samples.shape == samples_shape