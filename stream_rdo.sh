./build/mdaq crate-config.yaml build/out.fifo &
cat build/out.fifo | pipe_mux
