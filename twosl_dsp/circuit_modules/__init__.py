"""Circuit modules: one modelled piece of hardware per module file, built from techniques (architecture/dsp-blocks.md).
Each holds one `CircuitModule` subclass (twosl_dsp/gen_blocks.py) whose inputs are the circuit's controls and CV in its
units, whose build character is a frozen dataclass of numbers, and which cites its circuit's file in
references/circuits/."""
