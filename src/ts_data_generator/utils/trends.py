import numpy as np

def generate_time_series_wave_with_noise(amplitude, freq, phase, noise_level, timestamps):
    """
    Generate a sinusoidal wave with added noise.
    
    Parameters:
        amplitude (float): Amplitude of the sinusoidal wave.
        freq (float): Frequency of the sinusoidal wave.
        phase (float): Phase offset of the sinusoidal wave.
        noise_level (float): Standard deviation of the noise.
        
    Returns:
        y (numpy.ndarray): Sinusoidal wave with noise.
    """

    # frequency is in hours, phase is in minutes,
    # convert frequency to period
    frequency = 1/freq  # Set frequency to oscillate once every hour
    phase_hours = phase / 60  # Convert phase to hours
    noise_level = noise_level * 0.1 # Add 10% noise

    base_wave = np.zeros(len(timestamps))

    # Convert phase from minutes to hours
    
    base_wave += amplitude *np.sin(2 * np.pi * frequency * (timestamps.hour + timestamps.minute / 60)) + phase_hours

   
    noise = np.random.normal(0, noise_level, len(timestamps))  # Generate noise
    base_wave += noise  # Add noise to the wave
    
    # Add noise to the wave
    y = base_wave #+ noise
    
    return timestamps,y