`timescale 1ns / 1ps
module single_port_ram (
	input clk,
	input we,
	input [7:0] data,
	input [5:0] addr,
	output [7:0] q
);

	reg [7:0] ram[63:0];
	reg [5:0] addr_reg;

	always@(posedge clk)
	begin
		if (we)
			ram[addr] <= data;
		addr_reg <= addr;
	end
	assign q = ram[addr_reg];

//	initial begin
//		$dumpfile("waveform.vcd");
//		$dumpvars(0, single_port_ram);
//	end	

endmodule
