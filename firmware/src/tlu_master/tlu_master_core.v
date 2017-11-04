/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved 
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */
`timescale 1ps/1ps
`default_nettype none

module tlu_master_core
#(
    parameter ABUSWIDTH = 16
)(
    input wire CLK320,
    input wire CLK160,
    input wire CLK40,
    
    input wire TEST_PULSE,
    output wire [5:0] DUT_TRIGGER, DUT_RESET, 
    input  wire [5:0] DUT_BUSY, DUT_CLOCK,
    input  wire [3:0] BEAM_TRIGGER,

    input wire FIFO_READ,
    output wire FIFO_EMPTY,
    output wire [31:0] FIFO_DATA,

    input wire BUS_CLK,
    input wire [ABUSWIDTH-1:0] BUS_ADD,
    input wire [7:0] BUS_DATA_IN,
    output reg [7:0] BUS_DATA_OUT,
    input wire BUS_RST,
    input wire BUS_WR,
    input wire BUS_RD
    
);

localparam VERSION = 1;

wire SOFT_RST, START;
assign SOFT_RST = (BUS_ADD==0 && BUS_WR); 
assign START = (BUS_ADD==1 && BUS_WR);
    
wire RST;
assign RST = BUS_RST | SOFT_RST; 

reg [7:0] status_regs[8:0];

wire CONF_DONE;
wire [3:0] CONF_EN_INPUT;
assign CONF_EN_INPUT = status_regs[3][3:0];
wire [3:0] CONF_INPUT_INVERT;
assign CONF_INPUT_INVERT = status_regs[3][7:4];
    
wire [4:0] CONF_MAX_LE_DISTANCE;
assign CONF_MAX_LE_DISTANCE = status_regs[4][4:0];
wire [4:0] CONF_DIG_TH_INPUT;
assign CONF_DIG_TH_INPUT = status_regs[5][4:0];
wire [5:0] CONF_EN_OUTPUT;
assign CONF_EN_OUTPUT = status_regs[6][5:0];
reg [7:0] SKIP_TRIG_COUNTER;
reg [7:0] TIMEOUT_COUNTER;

wire [15:0] CONF_TIME_OUT;
assign CONF_TIME_OUT = {status_regs[8], status_regs[7]};
    
reg [63:0] TIME_STAMP;
reg [31:0] TRIG_ID;
    
reg [7:0] LOST_DATA_CNT; 
reg [63:0] TIME_STAMP_BUF; 
reg [31:0] TRIG_ID_BUF;
    
always @(posedge BUS_CLK) begin
    if(RST) begin
        status_regs[0] <= 8'b0;
        status_regs[1] <= 8'b0;
        status_regs[2] <= 8'b0;
        status_regs[3] <= 8'b0;
        status_regs[4] <= 8'b0;
		status_regs[5] <= 8'b0;
        status_regs[6] <= 8'b0;
        status_regs[7] <= 8'hff; //TIMEOUT
        status_regs[8] <= 8'hff;
    end
    else if(BUS_WR && BUS_ADD < 9)
        status_regs[BUS_ADD[3:0]] <= BUS_DATA_IN;
end

always @(posedge BUS_CLK) begin
    if(BUS_RD) begin
        if (BUS_ADD == 0)
            BUS_DATA_OUT <= VERSION;
        else if(BUS_ADD == 1)
            BUS_DATA_OUT <= {7'b0, CONF_DONE}; 
        else if(BUS_ADD == 2)
            BUS_DATA_OUT <= {8'b0}; //TODO: MODE;
        else if(BUS_ADD == 3)
            BUS_DATA_OUT <= {CONF_INPUT_INVERT, CONF_EN_INPUT};
        else if(BUS_ADD == 4)
            BUS_DATA_OUT <= {3'b0, CONF_MAX_LE_DISTANCE};
        else if(BUS_ADD == 5)
            BUS_DATA_OUT <= {3'b0, CONF_DIG_TH_INPUT};
        else if(BUS_ADD == 6)
            BUS_DATA_OUT <= {2'b0, CONF_EN_OUTPUT};
        else if(BUS_ADD == 7)
            BUS_DATA_OUT <= CONF_TIME_OUT[7:0];
         else if(BUS_ADD == 8)
            BUS_DATA_OUT <= CONF_TIME_OUT[15:8];
         
        else if(BUS_ADD == 16)
            BUS_DATA_OUT <= TIME_STAMP[7:0];
        else if(BUS_ADD == 17)
            BUS_DATA_OUT <= TIME_STAMP_BUF[15:8];
        else if(BUS_ADD == 18)
            BUS_DATA_OUT <= TIME_STAMP_BUF[23:16];
        else if(BUS_ADD == 19)
            BUS_DATA_OUT <= TIME_STAMP_BUF[31:24];
        else if(BUS_ADD == 20)
            BUS_DATA_OUT <= TIME_STAMP_BUF[39:32];
        else if(BUS_ADD == 21)
            BUS_DATA_OUT <= TIME_STAMP_BUF[47:40];
        else if(BUS_ADD == 22)
            BUS_DATA_OUT <= TIME_STAMP_BUF[55:48];
        else if(BUS_ADD == 23)
            BUS_DATA_OUT <= TIME_STAMP_BUF[63:56];
        else if(BUS_ADD == 24)
            BUS_DATA_OUT <= TRIG_ID[7:0];
        else if(BUS_ADD == 25)
            BUS_DATA_OUT <= TRIG_ID_BUF[15:8];
        else if(BUS_ADD == 26)
            BUS_DATA_OUT <= TRIG_ID_BUF[23:16];
        else if(BUS_ADD == 27)
            BUS_DATA_OUT <= TRIG_ID_BUF[31:24];
        else if(BUS_ADD == 28)
            BUS_DATA_OUT <= SKIP_TRIG_COUNTER;
        else if(BUS_ADD == 29)
            BUS_DATA_OUT <= TIMEOUT_COUNTER;
        else
            BUS_DATA_OUT <= 0;
    end
end

//TODO: THIS SHULD BE GRAY CODED ETC.... for CDC
always @ (posedge BUS_CLK) begin
    if (RST)
        TIME_STAMP_BUF <= 32'b0;
    else if (BUS_ADD == 16 && BUS_RD)
            TIME_STAMP_BUF <= TIME_STAMP;
end
always @ (posedge BUS_CLK) begin
    if (RST)
        TRIG_ID_BUF <= 32'b0;
    else if (BUS_ADD == 24 && BUS_RD)
            TRIG_ID_BUF <= TRIG_ID;
end

wire RST_SYNC;
cdc_reset_sync rst_pulse_sync (.clk_in(BUS_CLK), .pulse_in(RST), .clk_out(CLK40), .pulse_out(RST_SYNC));

wire START_SYNC;
cdc_pulse_sync start_pulse_sync (.clk_in(BUS_CLK), .pulse_in(START), .clk_out(CLK40), .pulse_out(START_SYNC));


wire [7:0] LAST_RISING_REL [3:0]; 
wire [3:0] VALID;
    
always@(posedge CLK40)
    if(RST_SYNC || START_SYNC)
        TIME_STAMP <= 0;
    else if(TIME_STAMP != 64'hffffffff_ffffffff)
        TIME_STAMP <= TIME_STAMP + 1;

genvar ch;
generate
for (ch = 0; ch < 4; ch = ch + 1) begin: tlu_ch
    
    tlu_ch_rx tlu_ch_rx (
        .RST(RST_SYNC),
        
        .CLK320(CLK320),
        .CLK160(CLK160),
        .CLK40(CLK40),
        .TIME_STAMP(TIME_STAMP[3:0]),
        
        .EN_INVERT(CONF_INPUT_INVERT[ch]),
        .TLU_IN(BEAM_TRIGGER[ch]),
        
        .DIG_TH(CONF_DIG_TH_INPUT),
        .EN(CONF_EN_INPUT[ch]),
        
        .VALID(VALID[ch]),
        .LAST_RISING(), 
        .LAST_FALLING(), 
        .LAST_TOT(),
        .LAST_RISING_REL(LAST_RISING_REL[ch])
    );
end
endgenerate 
    
reg [7:0] MIN_LE;
integer imin;

always @ (LAST_RISING_REL[0] or LAST_RISING_REL[1] or LAST_RISING_REL[2] or LAST_RISING_REL[3] or CONF_EN_INPUT) begin
    MIN_LE = 8'hff;
    for(imin = 0; imin <4; imin = imin+1) begin
        if (CONF_EN_INPUT[imin] && LAST_RISING_REL[imin] < MIN_LE)
            MIN_LE = LAST_RISING_REL[imin];
    end
end

reg [7:0] MAX_LE;
integer imax;

always @ (LAST_RISING_REL[0] or LAST_RISING_REL[1] or LAST_RISING_REL[2] or LAST_RISING_REL[3] or CONF_EN_INPUT)  begin
    MAX_LE = 0;
    for(imax = 0; imax <4; imax = imax+1) begin
        if (CONF_EN_INPUT[imax] && LAST_RISING_REL[imax] > MAX_LE)
            MAX_LE = LAST_RISING_REL[imax];
    end
end

wire [7:0] LE_DISTANCE;
assign LE_DISTANCE = MAX_LE - MIN_LE;
wire GEN_TRIG;
assign GEN_TRIG = ((LE_DISTANCE < CONF_MAX_LE_DISTANCE) && (VALID == CONF_EN_INPUT) && (CONF_EN_INPUT > 0))  || TEST_PULSE;

reg [1:0] GEN_TRIG_FF;
always@(posedge CLK40)
        GEN_TRIG_FF <= {GEN_TRIG_FF[0], GEN_TRIG};

wire [5:0] READY;
wire GEN_TRIG_PULSE;
wire TRIG_PULSE = (GEN_TRIG_FF[0] == 1 & GEN_TRIG_FF[1] == 0);
//wire TRIG_PULSE = (GEN_TRIG_FF[0] == 0 & GEN_TRIG == 1);
assign GEN_TRIG_PULSE =  TRIG_PULSE & (&READY);

wire SKIP_TRIGGER = TRIG_PULSE & !GEN_TRIG_PULSE;

always@(posedge CLK40)
    if(RST_SYNC | START_SYNC)
        SKIP_TRIG_COUNTER <= 0;
    else if(SKIP_TRIGGER & SKIP_TRIG_COUNTER!=8'hff )
        SKIP_TRIG_COUNTER <= SKIP_TRIG_COUNTER + 1;


always@(posedge CLK40)
    if(RST_SYNC | START_SYNC)
        TRIG_ID <= 0; //32'h3fff-10;
    else if(GEN_TRIG_PULSE && TRIG_ID!=32'hffffffff )
        TRIG_ID <= TRIG_ID + 1;

reg [31:0] TRIG_ID_FF;
always@(posedge CLK40)
    TRIG_ID_FF <= TRIG_ID;
        
localparam INV_OUT = 6'b101010;
wire [5:0] TIME_OUT;
genvar dut_ch;
generate
for (dut_ch = 0; dut_ch < 6; dut_ch = dut_ch + 1) begin: dut_ch_tx
    tlu_tx 
        #(
            .INV_OUT(INV_OUT[dut_ch])
        ) 
        tlu_tx( 
            .SYS_CLK(CLK40), 
            .CLK320(CLK320),
            .CLK160(CLK160),
            
            .TRIG_LE(MAX_LE[3:0]), 
            .SYS_RST(RST_SYNC), 
            .ENABLE(CONF_EN_OUTPUT[dut_ch]), 
            .TRIG(GEN_TRIG_PULSE),
            .TRIG_ID(TRIG_ID_FF[14:0]),
            .READY(READY[dut_ch]),
            .CONF_TIME_OUT(CONF_TIME_OUT),
            .TIME_OUT(TIME_OUT[dut_ch]),
            
            .TLU_CLOCK(DUT_CLOCK[dut_ch]), .TLU_BUSY(DUT_BUSY[dut_ch]),
            .TLU_TRIGGER(DUT_TRIGGER[dut_ch]), .TLU_RESET(DUT_RESET[dut_ch])
        );
end
endgenerate 

always@(posedge CLK40)
    if(RST_SYNC | START_SYNC)
        TIMEOUT_COUNTER <= 0;
    else if( (|TIME_OUT) & TIMEOUT_COUNTER!=8'hff )
        TIMEOUT_COUNTER <= TIMEOUT_COUNTER + 1;
    
//assign DUT_RESET = {2'b0,SKIP_TRIGGER ,&READY, DUT_BUSY[0], GEN_TRIG_PULSE} ;

endmodule
