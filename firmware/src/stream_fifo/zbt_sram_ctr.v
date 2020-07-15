/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */

`timescale 1ps/1ps
`default_nettype none

module zbt_sram_ctl(
    input wire CLK, CLK2X,
    input wire RESET,

    input wire [22:0] ADDR_WR,
    input wire [22:0] ADDR_RD,
    input wire [15:0] DATA_IN,
    input wire WE,
    input wire RD,
    output reg [15:0] DATA_OUT,
    output reg DATA_OUT_VALID,

    output wire SRAM_CLK,
    output wire  [22:0] SRAM_ADD,
    inout  wire [17:0] SRAM_DATA,
    output wire SRAM_ADV_LD_N,
    output wire [1:0] SRAM_BW_N,
    output wire SRAM_OE_N,
    output wire SRAM_WE_N
);

reg [15:0] write_data_q [3:0];
reg [22:0] write_addr_q [3:0];
reg [3:0] we_q, re_q;

ODDR sram_clk_oddr(
    .D1(1'b0), .D2(1'b1),
    .C(CLK2X), .CE(1'b1), .R(1'b0), .S(1'b0),
    .Q(SRAM_CLK)
);

always @ (posedge CLK) begin
   write_addr_q[0] <=  ADDR_WR;
   write_addr_q[1] <=  write_addr_q[0];
   write_addr_q[2] <=  write_addr_q[1];
   write_addr_q[3] <=  write_addr_q[2];
end

always @ (posedge CLK) begin
   write_data_q[0] <=  DATA_IN;
   write_data_q[1] <=  write_data_q[0];
   write_data_q[2] <=  write_data_q[1];
   write_data_q[3] <=  write_data_q[2];
end


always @ (posedge CLK)
    if(RESET)
        re_q <= 0;
    else
        re_q <= {re_q[2:0], RD};

always @ (posedge CLK)
    if(RESET)
        we_q <= 0;
    else
        we_q <= {we_q[2:0], WE};

assign SRAM_ADV_LD_N = 1'b0;
assign SRAM_BW_N = 2'b0;

always @(posedge CLK)
    DATA_OUT_VALID <= re_q[0];

ODDR sram_we(
    .D1(~we_q[0]), .D2(1'b1),
    .C(CLK), .CE(1'b1), .R(1'b0), .S(1'b0),
    .Q(SRAM_WE_N)
    );

ODDR sram_oe(
    .D1(1'b1), .D2(1'b0),
    .C(CLK), .CE(1'b1), .R(1'b0), .S(1'b0),
    .Q(SRAM_OE_N)
    );

genvar ch;
generate

for (ch = 0; ch < 23; ch = ch + 1) begin: addr_ch
    ODDR sram_addr(
    .D1(write_addr_q[0][ch]), .D2(ADDR_RD[ch]),
    .C(CLK), .CE(1'b1), .R(1'b0), .S(1'b0),
    .Q(SRAM_ADD[ch])
    );
end
endgenerate

reg [17:0] sram_data_out;
always @(posedge CLK2X)
    sram_data_out <= {2'b00, write_data_q[1]};

reg out_en_pre = 0;
always @(posedge CLK2X)
    if(out_en_pre)
        out_en_pre <= 0;
    else if(we_q[1])
        out_en_pre <= 1;

reg out_en;
always @(posedge CLK2X)
    out_en <= out_en_pre;

assign SRAM_DATA = out_en ? sram_data_out : 18'bz  ;

wire [17:0] DATA_2X;
genvar ch_d;
generate
for (ch_d = 0; ch_d < 18; ch_d = ch_d + 1) begin: data_ch
    IDDR sram_data(
    .Q1(), .Q2(DATA_2X[ch_d]),
    .C(CLK2X), .CE(1'b1), .R(1'b0), .S(1'b0),
    .D(SRAM_DATA[ch_d])
    );
end
endgenerate

always @(posedge CLK)
    DATA_OUT <= DATA_2X[15:0];

endmodule
