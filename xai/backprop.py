import tensorflow as tf
from tensorflow.keras.backend import gradients

class Backpropagation:
    def __init__(self, model, layer_name, input_data, layer_idx=None, masking=None):
        self.model = model
        self.layer_name = layer_name
        self.layer = model.get_layer(layer_name)
        self.input_data = input_data

        # Determine layer index if not provided
        if layer_idx is None:
            for i, layer in enumerate(self.model.layers):
                if layer.name == self.layer_name:
                    self.layer_idx = i
                    break
        else:
            self.layer_idx = layer_idx

        # Generate default masking if not provided
        if masking is None:
            shape = [1] + list(self.layer.output_shape[1:])
            masking = np.ones(shape, dtype=np.float32)  # Ensure numpy dtype
        self.masking = tf.convert_to_tensor(masking, dtype=tf.float32)  # Convert to TensorFlow tensor

    def compute(self):
        # Ensure masking is a tensor
        masking_tensor = tf.convert_to_tensor(self.masking, dtype=tf.float32)

        # Calculate loss using TensorFlow's reduce_mean
        loss = tf.reduce_mean(self.layer.output * masking_tensor)

        # Compute gradients (symbolic tensor in the computation graph)
        symbolic_gradients = gradients(loss, self.model.input)[0]

        # Define a Keras Model to compute gradients
        gradient_model = tf.keras.models.Model(inputs=self.model.input, outputs=symbolic_gradients)

        # Evaluate gradients with the actual input data
        output_data = gradient_model(self.input_data)

        # Process the gradients
        output_data = self.filter_gradient(output_data)
        return output_data

    @staticmethod
    def filter_gradient(x):
        x_abs = np.abs(x)
        x_max = np.amax(x_abs, axis=-1)
        return x_max
