/**
 * ------------------------------------------------------------
 * Copyright (c) SILAB , Physics Institute of Bonn University 
 * ------------------------------------------------------------
 */

`timescale 1ps / 1ps

`include "firmware/src/tlu.v"
 
module tb (
    input wire           BUS_CLK,
    input wire           BUS_RST,
    input wire   [31:0]  BUS_ADD,
    inout wire   [31:0]  BUS_DATA,
    input wire           BUS_RD,
    input wire           BUS_WR,
    output wire          BUS_BYTE_ACCESS
);

wire [15:0] ZEST_BUS_ADD;
assign ZEST_BUS_ADD = BUS_ADD[15:0] + 16'h2000;
    
tlu dut (
        .BUS_CLK_IN(BUS_CLK),
        .USB_BUS_ADD(ZEST_BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_OE_N(!BUS_RD),
        .BUS_RD_N(!BUS_RD),
        .BUS_WR_N(!BUS_WR),
        .BUS_CS_N(!(BUS_RD || BUS_WR))
);   

assign BUS_BYTE_ACCESS = BUS_ADD < 32'h8000_0000 ? 1'b1 : 1'b0;

initial begin
    
    $dumpfile("tlu.vcd");
    $dumpvars(0);

end

endmodule
