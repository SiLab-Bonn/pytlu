/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */

`timescale 1ps/1ps
`default_nettype none

module stream_fifo_core
#(
    parameter ABUSWIDTH = 16
)(
    input wire BUS_CLK,
    input wire [ABUSWIDTH-1:0] BUS_ADD,
    input wire [7:0] BUS_DATA_IN,
    output reg [7:0] BUS_DATA_OUT,
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

    input wire USB_STREAM_CLK,
    input wire STREAM_READY,
    output reg STREAM_WRITE_N,
    output reg [15:0] STREAM_DATA

);

localparam VERSION = 1;

wire SOFT_RST, LOCKED;
assign SOFT_RST = (BUS_ADD==0 && BUS_WR);

wire RST;
assign RST = BUS_RST | SOFT_RST | !LOCKED;

wire [23:0] CONF_SIZE_BYTE; // write data count in units of bytes
reg [22:0] CONF_SIZE; // in units of 2 bytes (16 bit)
assign CONF_SIZE_BYTE = CONF_SIZE * 2;
reg [23:0] CONF_SIZE_BYTE_BUF;

reg [7:0] status_regs[3:0];

always @(posedge BUS_CLK) begin
    if(RST) begin
        status_regs[0] <= 8'b0;
        status_regs[1] <= 8'b0;
        status_regs[2] <= 8'b0;
        status_regs[3] <= 8'b0;
    end
    else if(BUS_WR && BUS_ADD < 4)
        status_regs[BUS_ADD[1:0]] <= BUS_DATA_IN;
end

wire [23:0] CONF_READ_COUNT;
assign CONF_READ_COUNT = {status_regs[3], status_regs[2], status_regs[1]};

reg [1:0] start_count_ff;
always @(posedge BUS_CLK)
    start_count_ff <= {start_count_ff[0], (BUS_ADD==3 && BUS_WR)};

wire START_COUNT = start_count_ff[1]==0 & start_count_ff[0]==1;

always @ (posedge BUS_CLK) begin //(*) begin
    if(BUS_RD) begin
        if(BUS_ADD == 0)
            BUS_DATA_OUT <= VERSION;
        else if(BUS_ADD == 1)
            BUS_DATA_OUT <= CONF_READ_COUNT[7:0]; // in units of 2*bytes
        else if(BUS_ADD == 2)
            BUS_DATA_OUT <= CONF_READ_COUNT[15:8];
        else if(BUS_ADD == 3)
            BUS_DATA_OUT <= CONF_READ_COUNT[23:16];
        else if(BUS_ADD == 4)
            BUS_DATA_OUT <= CONF_SIZE_BYTE[7:0]; // in units of bytes
        else if(BUS_ADD == 5)
            BUS_DATA_OUT <= CONF_SIZE_BYTE_BUF[15:8];
        else if(BUS_ADD == 6)
            BUS_DATA_OUT <= CONF_SIZE_BYTE_BUF[22:16];
        else
            BUS_DATA_OUT <= 8'b0;
    end
end

always @ (posedge BUS_CLK)
begin
    if (BUS_ADD == 4 && BUS_RD)
        CONF_SIZE_BYTE_BUF <= CONF_SIZE_BYTE;
end

wire U1_CLK0;
wire STREAM_CLK, STREAM_CLK_FB;
wire U1_CLK2X;

DCM #(
    .CLKDV_DIVIDE(6),
    .CLKFX_DIVIDE(3),
    .CLKFX_MULTIPLY(10),
    .CLKIN_DIVIDE_BY_2("FALSE"),
    .CLKIN_PERIOD(20.833),
    .CLKOUT_PHASE_SHIFT("NONE"),
    .CLK_FEEDBACK("1X"),
    .DESKEW_ADJUST("SYSTEM_SYNCHRONOUS"),
    .DFS_FREQUENCY_MODE("LOW"),
    .DLL_FREQUENCY_MODE("LOW"),
    .DUTY_CYCLE_CORRECTION("TRUE"),
    .FACTORY_JF(16'h8080),
    .PHASE_SHIFT(0),
    .STARTUP_WAIT("TRUE")
) DCM_BUS (
    .CLKFB(STREAM_CLK_FB),
    .CLKIN(USB_STREAM_CLK),
    .DSSEN(1'b0),
    .PSCLK(1'b0),
    .PSEN(1'b0),
    .PSINCDEC(1'b0),
    .RST(1'b0),
    .CLKDV(),
    .CLKFX(),
    .CLKFX180(),
    .CLK0(U1_CLK0),
    .CLK2X(U1_CLK2X),
    .CLK2X180(),
    .CLK90(),
    .CLK180(),
    .CLK270(),
    .LOCKED(LOCKED),
    .PSDONE(),
    .STATUS()
);


wire STREAM_CLK2X;
BUFG CLK_STREAM_BUFG_INST (.I(U1_CLK0), .O(STREAM_CLK_FB));
assign STREAM_CLK = STREAM_CLK_FB;

BUFG CLK_STREAM2X_BUFG_INST (.I(U1_CLK2X), .O(STREAM_CLK2X));

wire STREAM_RST;
cdc_reset_sync rst_pulse_sync (.clk_in(BUS_CLK), .pulse_in(RST), .clk_out(STREAM_CLK), .pulse_out(STREAM_RST));

wire cdc_count_empty;
wire [23:0] cdc_data_count;
cdc_syncfifo #(.DSIZE(24), .ASIZE(3)) cdc_syncfifo_count
(
    .rdata(cdc_data_count),
    .wfull(),
    .rempty(cdc_count_empty),
    .wdata(CONF_READ_COUNT),
    .winc(START_COUNT), .wclk(BUS_CLK), .wrst(RST),
    .rinc(1'b1), .rclk(STREAM_CLK), .rrst(STREAM_RST)
);

reg [18:0] sram_addr_rd;
reg [18:0] sram_addr_wr;

reg sram_read;
wire sram_full, sram_write, sram_empty;

reg [23:0] count;
always @(posedge STREAM_CLK)
    if(STREAM_RST)
        count <= 0;
    else if(!cdc_count_empty)
        count <= cdc_data_count/2;
    else if(sram_read & count!=0)
        count <= count - 1;

reg [18:0] sram_rd_end;
always @(posedge STREAM_CLK)
    if(STREAM_RST)
        sram_rd_end <= 0;
    else if(!cdc_count_empty)
        sram_rd_end <= {sram_addr_wr[18:3], 3'b000};

reg sram_rd_addr_inc;
always @(posedge STREAM_CLK)
    if(STREAM_RST)
        sram_rd_addr_inc <= 0;
    else if(!cdc_count_empty & !sram_empty)
        sram_rd_addr_inc <= 1;
    else if(sram_rd_end==sram_addr_rd)
        sram_rd_addr_inc <= 0;

wire cdc_wfull, cdc_empty;
assign FIFO_READ_NEXT_OUT = !cdc_wfull & !FIFO_EMPTY_IN;
wire [15:0] cdc_data_out;

cdc_syncfifo #(.DSIZE(16), .ASIZE(3)) cdc_syncfifo
(
    .rdata(cdc_data_out),
    .wfull(cdc_wfull),
    .rempty(cdc_empty),
    .wdata(FIFO_DATA),
    .winc(!FIFO_EMPTY_IN), .wclk(BUS_CLK), .wrst(RST),
    .rinc(sram_write), .rclk(STREAM_CLK), .rrst(STREAM_RST)
);

assign sram_write = !cdc_empty & !sram_full;
always@(posedge STREAM_CLK) begin
    if(STREAM_RST)
        sram_addr_wr <= 0;
    else if(sram_write)
        sram_addr_wr <= sram_addr_wr + 1;
end

always@(posedge STREAM_CLK) begin
    if(STREAM_RST)
        sram_addr_rd <= 0;
    else if(sram_read & count!=0 & sram_rd_end!=sram_addr_rd)
        sram_addr_rd <= sram_addr_rd + 1;
end

wire [18:0] sram_addr_wr_next;
assign sram_addr_wr_next = sram_addr_wr + 1;

assign sram_full = sram_addr_wr_next == sram_addr_rd;
assign sram_empty = (sram_addr_wr == sram_addr_rd);

reg [18:0] sram_size_stream;
always @ (posedge STREAM_CLK)
    sram_size_stream <= sram_addr_wr - sram_addr_rd;

//TODO:This should be synchronized clock-domain-crossing, IT IS WRONG LIKE THIS
always @ (posedge BUS_CLK)
    CONF_SIZE <= sram_size_stream;

wire stream_data_valid;
wire [15:0] sram_data_out;

zbt_sram_ctl zbt_sram_ctl(
    .CLK(STREAM_CLK),
    .CLK2X(STREAM_CLK2X),
    .RESET(STREAM_RST),

    .ADDR_WR({4'b0, sram_addr_wr}),
    .ADDR_RD({4'b0, sram_addr_rd}),
    .DATA_IN(cdc_data_out),
    .WE(sram_write),
    .RD(sram_read),
    .DATA_OUT(sram_data_out),
    .DATA_OUT_VALID(stream_data_valid),

    .SRAM_CLK(SRAM_CLK),
    .SRAM_ADD(SRAM_ADD),
    .SRAM_DATA(SRAM_DATA),
    .SRAM_ADV_LD_N(SRAM_ADV_LD_N),
    .SRAM_BW_N(SRAM_BW_N),
    .SRAM_OE_N(SRAM_OE_N),
    .SRAM_WE_N(SRAM_WE_N)
);

reg is_data_out;
always @(negedge STREAM_CLK)
    if(STREAM_RST)
        is_data_out <= 0;
    else if(sram_read)
        is_data_out <= sram_rd_addr_inc;

always @(negedge STREAM_CLK)
    STREAM_DATA <= is_data_out ? sram_data_out : 16'b0;

always @(negedge STREAM_CLK)
    STREAM_WRITE_N <= !stream_data_valid;

//This is one big HACK!
reg [2:0] fsm;
always@(posedge STREAM_CLK)
    if(STREAM_RST)
        fsm <= 0;
    else if (fsm != 0)
        fsm <= fsm + 1;
    else if(STREAM_READY & count!=0)
        fsm <= 1;

reg stream_ready_ff;
always@(posedge STREAM_CLK)
    stream_ready_ff <= STREAM_READY;

always@(posedge STREAM_CLK)
    sram_read <= fsm == 2 & stream_ready_ff;

/*
`ifndef COCOTB_SIM
wire [35:0] control_bus;
chipscope_icon ichipscope_icon
(
    .CONTROL0(control_bus)
);
chipscope_ila ichipscope_ila
(
    .CONTROL(control_bus),
    .CLK(STREAM_CLK),
    .TRIG0({count, stream_data_valid, sram_read, cdc_count_empty, stream_ready_ff})
);

`endif
*/


endmodule
