def closest_ssb_aligned_arfcn(desired_freq_mhz):
    # Convert MHz to kHz to work with integers
    desired_freq_khz = int(desired_freq_mhz * 1000)

    # 3GPP TS 38.104 Reference Constants for FR1 (in kHz)
    freq_ref_khz = 3000000  # 3000 MHz
    arfcn_ref = 600000
    arfcn_step_khz = 15  #  Correct step for FR1 (15 kHz)

    # SSB raster alignment rule (must be a multiple of 1440 kHz from 3000 MHz)
    ssb_raster_base_khz = 3000000  # 3000 MHz
    ssb_raster_step_khz = 1440  # 1.44 MHz = 1440 kHz

    # Compute the two nearest valid SSB raster-aligned frequencies (in kHz)
    N_lower = (desired_freq_khz - ssb_raster_base_khz) // ssb_raster_step_khz
    N_upper = N_lower + 1  # Next step up

    freq_lower_khz = ssb_raster_base_khz + (N_lower * ssb_raster_step_khz)
    freq_upper_khz = ssb_raster_base_khz + (N_upper * ssb_raster_step_khz)

    # Pick the closest aligned frequency
    aligned_freq_khz = min([freq_lower_khz, freq_upper_khz], key=lambda f: abs(f - desired_freq_khz))

    # Ensure the frequency is correctly on the SSB raster
    if (aligned_freq_khz - ssb_raster_base_khz) % ssb_raster_step_khz != 0:
        raise ValueError("SSB alignment failed.")

    # Compute ARFCN using the **correct 15 kHz step size** (all integer math)
    arfcn = arfcn_ref + ((aligned_freq_khz - freq_ref_khz) // arfcn_step_khz)

    return {
        "desired_freq_mhz": desired_freq_mhz,
        "aligned_freq_mhz": aligned_freq_khz / 1000.0,  # Convert back to MHz
        "arfcn": arfcn
    }

if __name__ == "__main__":
    try:
        desired_freq = float(input("Enter desired frequency in MHz: "))
        result = closest_ssb_aligned_arfcn(desired_freq)

        print(f"\nClosest valid ARFCN aligned with SSB raster:")
        print(f"  Desired Frequency:     {result['desired_freq_mhz']:.3f} MHz")
        print(f"  Closest Aligned Freq:  {result['aligned_freq_mhz']:.3f} MHz")
        print(f"  Valid ARFCN:           {result['arfcn']}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

