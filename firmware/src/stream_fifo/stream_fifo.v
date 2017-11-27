/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved 
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */
`timescale 1ps/1ps
`default_nettype none


module stream_fifo #(
    parameter BASEADDR = 16'h0000,
    parameter HIGHADDR = 16'h0000,
    parameter ABUSWIDTH = 16
)(
    input wire BUS_CLK,
    input wire [ABUSWIDTH-1:0] BUS_ADD,
    inout wire [7:0] BUS_DATA,
    input wire BUS_RST,
    input wire BUS_WR,
    input wire BUS_RD,

    output wire SRAM_CLK,
    output wire  [22:0] SRAM_ADD,
    inout  wire [17:0] SRAM_DATA,
    output wire SRAM_ADV_LD_N,
    output wire [1:0] SRAM_BW_N,
    output wire SRAM_OE_N,
    output wire SRAM_WE_N,
    
    output wire FIFO_READ_NEXT_OUT,
    input wire FIFO_EMPTY_IN,
    input wire [15:0] FIFO_DATA,

    input wire STREAM_CLK,
    input wire STREAM_READY,
    output wire STREAM_WRITE_N,
    output wire [15:0] STREAM_DATA
    

);

wire IP_RD, IP_WR;
wire [ABUSWIDTH-1:0] IP_ADD;
wire [7:0] IP_DATA_IN;
wire [7:0] IP_DATA_OUT;

bus_to_ip #(
    .BASEADDR(BASEADDR),
    .HIGHADDR(HIGHADDR),
    .ABUSWIDTH(ABUSWIDTH)
) i_bus_to_ip (
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),

    .IP_RD(IP_RD),
    .IP_WR(IP_WR),
    .IP_ADD(IP_ADD),
    .IP_DATA_IN(IP_DATA_IN),
    .IP_DATA_OUT(IP_DATA_OUT)
    );
    
    
stream_fifo_core #(
    .ABUSWIDTH(ABUSWIDTH)
) stream_fifo_core (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(IP_ADD),
    .BUS_DATA_IN(IP_DATA_IN),
    .BUS_RD(IP_RD),
    .BUS_WR(IP_WR),
    .BUS_DATA_OUT(IP_DATA_OUT),

    .SRAM_CLK(SRAM_CLK),
    .SRAM_ADD(SRAM_ADD),
    .SRAM_DATA(SRAM_DATA),
    .SRAM_ADV_LD_N(SRAM_ADV_LD_N),
    .SRAM_BW_N(SRAM_BW_N),
    .SRAM_OE_N(SRAM_OE_N),
    .SRAM_WE_N(SRAM_WE_N),
    
    .FIFO_READ_NEXT_OUT(FIFO_READ_NEXT_OUT),
    .FIFO_EMPTY_IN(FIFO_EMPTY_IN),
    .FIFO_DATA(FIFO_DATA),
    
    .USB_STREAM_CLK(STREAM_CLK),
    .STREAM_READY(STREAM_READY),
    .STREAM_WRITE_N(STREAM_WRITE_N),
    .STREAM_DATA(STREAM_DATA)
    
);

endmodule
