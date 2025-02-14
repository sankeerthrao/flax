# Copyright 2024 The Flax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# %%
import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
import numpy as np

from flax.experimental import nnx

X = np.linspace(0, 1, 100)[:, None]
Y = 0.8 * X**2 + 0.1 + np.random.normal(0, 0.1, size=X.shape)


def dataset(batch_size):
  while True:
    idx = np.random.choice(len(X), size=batch_size)
    yield X[idx], Y[idx]


class Linear(nnx.Module):
  def __init__(self, din: int, dout: int, *, rngs: nnx.Rngs):
    self.w = nnx.Param(jax.random.uniform(rngs.params(), (din, dout)))
    self.b = nnx.Param(jnp.zeros((dout,)))

  def __call__(self, x):
    return x @ self.w + self.b


class Count(nnx.Variable):
  pass


class MLP(nnx.Module):
  def __init__(self, din, dhidden, dout, *, rngs: nnx.Rngs):
    self.count = Count(jnp.array(0))
    self.linear1 = Linear(din, dhidden, rngs=rngs)
    self.linear2 = Linear(dhidden, dout, rngs=rngs)

  def __call__(self, x):
    self.count += 1
    x = self.linear1(x)
    x = jax.nn.relu(x)
    x = self.linear2(x)
    return x


model = MLP(din=1, dhidden=32, dout=1, rngs=nnx.Rngs(0))


@nnx.jit
def train_step(model: MLP, batch):
  x, y = batch

  def loss_fn(model: MLP):
    y_pred = model(x)
    return jnp.mean((y - y_pred) ** 2)

  #                                   |--default--|
  grad: nnx.State = nnx.grad(loss_fn, wrt=nnx.Param)(model)
  # sdg update
  model.update(
    jax.tree_map(lambda w, g: w - 0.1 * g, model.extract(nnx.Param), grad)
  )

  # no return!!!


@nnx.jit
def test_step(model: MLP, batch):
  x, y = batch
  y_pred = model(x)
  loss = jnp.mean((y - y_pred) ** 2)
  return {'loss': loss}


total_steps = 10_000
for step, batch in enumerate(dataset(32)):
  train_step(model, batch)

  if step % 1000 == 0:
    logs = test_step(model, (X, Y))
    print(f"step: {step}, loss: {logs['loss']}")

  if step >= total_steps - 1:
    break

print('times called:', model.count)

y_pred = model(X)

plt.scatter(X, Y, color='blue')
plt.plot(X, y_pred, color='black')
plt.show()
