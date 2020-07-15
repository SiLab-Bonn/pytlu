/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */

`timescale 1ps/1ps
`default_nettype none

`include "utils/reset_gen.v"
`include "utils/bus_to_ip.v"
`include "utils/clock_divider.v"
`include "utils/cdc_reset_sync.v"
`include "utils/ddr_des.v"
`include "utils/cdc_syncfifo.v"
`include "utils/generic_fifo.v"

`include "gpio/gpio.v"

`include "i2c/i2c.v"
`include "i2c/i2c_core.v"
`include "utils/cdc_pulse_sync.v"

`include "tlu_clk_gen.v"

`include "tlu_master/tlu_master.v"
`include "tlu_master/tlu_master_core.v"
`include "tlu_master/tlu_ch_rx.v"
`include "tlu_master/tlu_tx.v"

`include "pulse_gen/pulse_gen.v"
`include "pulse_gen/pulse_gen_core.v"

`include "stream_fifo/stream_fifo.v"
`include "stream_fifo/stream_fifo_core.v"
`include "stream_fifo/zbt_sram_ctr.v"

`ifdef COCOTB_SIM //for simulation
    `include "utils/BUFG_sim.v"
    `include "utils/IDDR_sim.v"
    `include "utils/DCM_sim.v"
    `include "utils/ODDR_sim.v"
`else
    `include "utils/IDDR_s3.v"
    `include "utils/ODDR_s3.v"
`endif


module tlu (
    input wire BUS_CLK_IN,
    input wire [15:0] USB_BUS_ADD,
    inout wire [7:0] BUS_DATA,
    input wire BUS_OE_N,
    input wire BUS_RD_N,
    input wire BUS_WR_N,
    input wire BUS_CS_N,

    input wire USB_STREAM_CLK,
    output wire [1:0] USB_STREAM_FIFOADDR,
    output wire USB_STREAM_PKTEND_N,
    input wire [2:0] USB_STREAM_FLAGS_N,
    output wire USB_STREAM_SLOE_n,
    output wire USB_STREAM_SLRD_n,
    (* IOB="TRUE" *)
    output wire USB_STREAM_SLWR_n,
    (* IOB="TRUE" *)
    output wire [15:0] USB_STREAM_DATA,
    input wire USB_STREAM_FX2RDY,

    //IO
    inout wire I2C_SCL_OUT, I2C_SDA_OUT,
    input wire I2C_SCL_IN, I2C_SDA_IN,
    output wire [1:0] I2C_SEL,

    output wire [5:0] DUT_TRIGGER, DUT_RESET,
    input  wire [5:0] DUT_BUSY, DUT_CLOCK,
    input  wire [3:0] BEAM_TRIGGER,

    output wire SRAM_CLK,
    output wire [22:0] SRAM_ADD,
    output wire SRAM_ADV_LD_N,
    output wire [1:0] SRAM_BW_N,
    inout wire [17:0] SRAM_DATA,
    output wire SRAM_OE_N,
    output wire SRAM_WE_N,

    output wire [3:0] DEBUG
);

//assign DUT_TRIGGER = {BEAM_TRIGGER, BEAM_TRIGGER[1:0]};
//assign DUT_RESET = DUT_BUSY;

(* KEEP = "{TRUE}" *)
wire CLK320;
(* KEEP = "{TRUE}" *)
wire CLK160;
(* KEEP = "{TRUE}" *)
wire CLK40;
(* KEEP = "{TRUE}" *)
wire CLK16;
(* KEEP = "{TRUE}" *)
wire BUS_CLK;
(* KEEP = "{TRUE}" *)
wire CLK8;
(* KEEP = "{TRUE}" *)
wire I2C_CLK;

wire CLK_LOCKED;

tlu_clk_gen tlu_clk_gen(
    .CLKIN(BUS_CLK_IN),
    .BUS_CLK(BUS_CLK),
    .U1_CLK8(CLK8),
    .U2_CLK16(CLK16),
    .U2_CLK40(CLK40),
    .U2_CLK160(CLK160),
    .U2_CLK320(CLK320),
    .U2_LOCKED(CLK_LOCKED)
);

wire BUS_RST;
reset_gen ireset_gen(.CLK(BUS_CLK), .RST(BUS_RST));

// -------  BUS SIGNALING  ------- //
wire BUS_RD, BUS_WR;
wire [15:0] BUS_ADD;
assign BUS_RD = !BUS_RD_N && !BUS_CS_N && !BUS_OE_N;
assign BUS_WR = !BUS_WR_N && !BUS_CS_N;
assign BUS_ADD = USB_BUS_ADD - 16'h2000;

// -------  MODULE ADDRESSES ------- //
localparam VERSION = 8'h05;

localparam GPIO_BASEADDR = 16'h3000;
localparam GPIO_HIGHADDR = 16'h4000-1;

localparam I2C_BASEADDR = 16'h4000;
localparam I2C_HIGHADDR = 16'h5000-1;

localparam TLU_MASTER_BASEADDR = 16'h5000;
localparam TLU_MASTER_HIGHADDR = 16'h6000 - 1;

localparam PULSE_TEST_BASEADDR = 16'h6000;
localparam PULSE_TEST_HIGHADDR = 16'h7000 - 1;

localparam FIFO_BASEADDR = 16'h7000;
localparam FIFO_HIGHADDR = 16'h8000 - 1;


// ------- MODULES  ------- //
reg RD_VERSION;
always@(posedge BUS_CLK)
    if(BUS_ADD == 16'h2000 && BUS_RD)
        RD_VERSION <= 1;
    else
        RD_VERSION <= 0;

assign BUS_DATA = (RD_VERSION) ? VERSION : 8'bz;

wire [7:0] GPIO;
gpio #(
    .BASEADDR(GPIO_BASEADDR),
    .HIGHADDR(GPIO_HIGHADDR),
    .IO_WIDTH(8),
    .IO_DIRECTION(8'hff)
) i_gpio (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .IO(GPIO[7:0])
);

assign I2C_SEL = GPIO[1:0];

wire I2C_CLK_PRE;
clock_divider #( .DIVISOR(480) ) i2c_clkdev ( .CLK(BUS_CLK), .RESET(BUS_RST), .CE(), .CLOCK(I2C_CLK_PRE) );
`ifdef COCOTB_SIM //for simulation
    BUFG BUFG_I2C (  .O(I2C_CLK),  .I(BUS_CLK) );
`else
    BUFG BUFG_I2C (  .O(I2C_CLK),  .I(I2C_CLK_PRE) );
`endif

i2c #(
    .BASEADDR(I2C_BASEADDR),
    .HIGHADDR(I2C_HIGHADDR),
    .MEM_BYTES(8),
    .IGNORE_ACK(1)
) i_i2c_out (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .I2C_CLK(I2C_CLK),
    .I2C_SDA(I2C_SDA_OUT),
    .I2C_SCL(I2C_SCL_OUT)
);

//THIS CANOT BE DONE BCAUSE THE PCB DESIGN IS WRONG!!!
//assign I2C_SDA_OUT = I2C_SDA_IN ? 1'bz : 1'b0;
//assign I2C_SCL_OUT = I2C_SCL_IN ? 1'bz : 1'b0;

`ifndef COCOTB_SIM //for simulation
    PULLUP isda (.O(I2C_SDA_OUT));
    PULLUP iscl (.O(I2C_SCL_OUT));
`else
    pullup  isda (I2C_SDA_OUT);
    pullup  iscl (I2C_SCL_OUT);
`endif

wire TEST_PULSE;
pulse_gen #(
    .BASEADDR(PULSE_TEST_BASEADDR),
    .HIGHADDR(PULSE_TEST_HIGHADDR)
) i_pulse_gen (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK(CLK40),
    .EXT_START(1'b0),
    .PULSE(TEST_PULSE)
);

wire TDC_MASTER_FIFO_READ, TDC_MASTER_FIFO_EMPTY;
wire [15:0] TDC_MASTER_FIFO_DATA;

tlu_master #(
    .BASEADDR(TLU_MASTER_BASEADDR),
    .HIGHADDR(TLU_MASTER_HIGHADDR)
) tlu_master (
    .CLK320(CLK320),
    .CLK160(CLK160),
    .CLK40(CLK40),

    .TEST_PULSE(TEST_PULSE),
    .DUT_TRIGGER(DUT_TRIGGER), .DUT_RESET(DUT_RESET),
    .DUT_BUSY(DUT_BUSY), .DUT_CLOCK(DUT_CLOCK),
    .BEAM_TRIGGER(BEAM_TRIGGER),

    .FIFO_READ(TDC_MASTER_FIFO_READ),
    .FIFO_EMPTY(TDC_MASTER_FIFO_EMPTY),
    .FIFO_DATA(TDC_MASTER_FIFO_DATA),

    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR)
);

wire STREAM_WRITE_N;
wire STREAM_READY;
stream_fifo #(
    .BASEADDR(FIFO_BASEADDR),
    .HIGHADDR(FIFO_HIGHADDR)
) stream_fifo (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .FIFO_READ_NEXT_OUT(TDC_MASTER_FIFO_READ),
    .FIFO_EMPTY_IN(TDC_MASTER_FIFO_EMPTY),
    .FIFO_DATA(TDC_MASTER_FIFO_DATA),

    .SRAM_CLK(SRAM_CLK),
    .SRAM_ADD(SRAM_ADD),
    .SRAM_DATA(SRAM_DATA),
    .SRAM_ADV_LD_N(SRAM_ADV_LD_N),
    .SRAM_BW_N(SRAM_BW_N),
    .SRAM_OE_N(SRAM_OE_N),
    .SRAM_WE_N(SRAM_WE_N),

    .STREAM_CLK(USB_STREAM_CLK),
    .STREAM_READY(STREAM_READY),
    .STREAM_WRITE_N(STREAM_WRITE_N),
    .STREAM_DATA(USB_STREAM_DATA)
);


assign USB_STREAM_PKTEND_N = 1'b1;
assign USB_STREAM_FIFOADDR = 2'b10;
assign USB_STREAM_SLRD_n = 1'b1;
assign USB_STREAM_SLOE_n = 1'b1;
assign USB_STREAM_SLWR_n = STREAM_WRITE_N;
assign STREAM_READY = (USB_STREAM_FLAGS_N[1] == 1'b1) & (USB_STREAM_FX2RDY == 1'b1);

/*
wire [35:0] control_bus;
chipscope_icon ichipscope_icon
(
    .CONTROL0(control_bus)
);
chipscope_ila ichipscope_ila
(
    .CONTROL(control_bus),
    .CLK(USB_STREAM_CLK),
    .TRIG0({USB_STREAM_DATA, USB_STREAM_FLAGS_N,USB_STREAM_FX2RDY, USB_STREAM_SLWR_n, USB_STREAM_CLK, BUS_CLK})
);
*/

/*
assign DEBUG[0] = STREAM_WRITE;
assign DEBUG[1] = STREAM_READY;
assign DEBUG[2] = USB_STREAM_CLK;
assign DEBUG[3] = BUS_CLK;
*/
//assign DEBUG = 0;

endmodule
