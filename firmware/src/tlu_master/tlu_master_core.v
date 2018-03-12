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
    output wire [15:0] FIFO_DATA,

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

reg [7:0] status_regs[9:0];

wire CONF_DONE;
wire [3:0] CONF_EN_INPUT;
assign CONF_EN_INPUT = status_regs[3][3:0];
wire [3:0] CONF_INPUT_INVERT;
assign CONF_INPUT_INVERT = status_regs[3][7:4];
    
wire [4:0] CONF_MAX_LE_DISTANCE;
assign CONF_MAX_LE_DISTANCE = status_regs[4][4:0];
wire [4:0] CONF_DIG_TH_INPUT;
assign CONF_DIG_TH_INPUT = status_regs[5][4:0];
wire [4:0] CONF_N_BITS_TRIGGER_ID;
assign CONF_N_BITS_TRIGGER_ID = status_regs[9][4:0];
wire [5:0] CONF_EN_OUTPUT;
assign CONF_EN_OUTPUT = status_regs[6][5:0];
reg [31:0] SKIP_TRIG_COUNTER;
reg [7:0] TIMEOUT_COUNTER;

wire [15:0] CONF_TIME_OUT;
assign CONF_TIME_OUT = {status_regs[8], status_regs[7]};
    
reg [63:0] TIME_STAMP;
reg [31:0] TRIG_ID;
    
reg [7:0] LOST_DATA_CNT; 
reg [63:0] TIME_STAMP_BUF; 
reg [31:0] TRIG_ID_BUF;
reg [31:0] SKIP_TRIG_COUNTER_BUF;
    
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
		  status_regs[9] <= 8'b0; //N_BITS_TRIGGER_ID
    end
    else if(BUS_WR && BUS_ADD < 10)
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
        else if(BUS_ADD == 9)
            BUS_DATA_OUT <= {3'b0, CONF_N_BITS_TRIGGER_ID};
         
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
            BUS_DATA_OUT <= SKIP_TRIG_COUNTER[7:0];
        else if(BUS_ADD == 29)
            BUS_DATA_OUT <= SKIP_TRIG_COUNTER_BUF[15:8];
        else if(BUS_ADD == 30)
            BUS_DATA_OUT <= SKIP_TRIG_COUNTER_BUF[23:16];
        else if(BUS_ADD == 31)
            BUS_DATA_OUT <= SKIP_TRIG_COUNTER_BUF[31:24];
        else if(BUS_ADD == 32)
            BUS_DATA_OUT <= TIMEOUT_COUNTER;
        else if(BUS_ADD == 33)
            BUS_DATA_OUT <= LOST_DATA_CNT;
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
always @ (posedge BUS_CLK) begin
    if (RST)
        SKIP_TRIG_COUNTER_BUF <= 32'b0;
    else if (BUS_ADD == 28 && BUS_RD)
            SKIP_TRIG_COUNTER_BUF <= SKIP_TRIG_COUNTER;
end


wire RST_SYNC;
cdc_reset_sync rst_pulse_sync (.clk_in(BUS_CLK), .pulse_in(RST), .clk_out(CLK40), .pulse_out(RST_SYNC));

wire START_SYNC;
cdc_pulse_sync start_pulse_sync (.clk_in(BUS_CLK), .pulse_in(START), .clk_out(CLK40), .pulse_out(START_SYNC));


wire [15:0] LAST_RISING_REL [3:0]; 
wire [3:0] VALID;
    
always@(posedge CLK40)
    if(RST_SYNC || START_SYNC)
        TIME_STAMP <= 1;
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
        .TIME_STAMP(TIME_STAMP[11:0]),
        
        .EN_INVERT(CONF_INPUT_INVERT[ch]),
        .TLU_IN(BEAM_TRIGGER[ch]),
        
        .DIG_TH({11'b0, CONF_DIG_TH_INPUT}),
        .EN(1'b1),
        
        .VALID(VALID[ch]),
        .LAST_RISING(), 
        .LAST_FALLING(), 
        .LAST_TOT(),
        .LAST_RISING_REL(LAST_RISING_REL[ch])
    );
end
endgenerate 
    
reg [15:0] MIN_LE;
integer imin;

always @ (LAST_RISING_REL[0] or LAST_RISING_REL[1] or LAST_RISING_REL[2] or LAST_RISING_REL[3] or CONF_EN_INPUT) begin
    MIN_LE = 16'hffff;
    for(imin = 0; imin <4; imin = imin+1) begin
        if (CONF_EN_INPUT[imin] && LAST_RISING_REL[imin] < MIN_LE)
            MIN_LE = LAST_RISING_REL[imin];
    end
end

reg [15:0] MAX_LE;
integer imax;

always @ (LAST_RISING_REL[0] or LAST_RISING_REL[1] or LAST_RISING_REL[2] or LAST_RISING_REL[3] or CONF_EN_INPUT)  begin
    MAX_LE = 0;
    for(imax = 0; imax <4; imax = imax+1) begin
        if (CONF_EN_INPUT[imax] && LAST_RISING_REL[imax] > MAX_LE)
            MAX_LE = LAST_RISING_REL[imax];
    end
end

wire [15:0] LE_DISTANCE;
assign LE_DISTANCE = MAX_LE - MIN_LE;
wire GEN_TRIG;
assign GEN_TRIG = ((LE_DISTANCE < CONF_MAX_LE_DISTANCE) && ( (VALID & CONF_EN_INPUT) == CONF_EN_INPUT) && (CONF_EN_INPUT > 0))  || TEST_PULSE;

reg [1:0] GEN_TRIG_FF;
always@(posedge CLK40)
        GEN_TRIG_FF <= {GEN_TRIG_FF[0], GEN_TRIG};

wire [5:0] READY;
wire GEN_TRIG_PULSE;
wire TRIG_PULSE = (GEN_TRIG_FF[0] == 1 & GEN_TRIG_FF[1] == 0);
//wire TRIG_PULSE = (GEN_TRIG_FF[0] == 0 & GEN_TRIG == 1);
assign GEN_TRIG_PULSE =  TRIG_PULSE & (&READY);

reg [10:0] GEN_CDC_FIFO_FF;  /// in tlu_ch_rx VALID goes F when realtive_le > 16*15 ...
wire GEN_CDC_FIFO_PULSE;
always@(posedge CLK40)
        GEN_CDC_FIFO_FF <= {GEN_CDC_FIFO_FF[10:0], GEN_TRIG_PULSE};
assign GEN_CDC_FIFO_PULSE= (GEN_CDC_FIFO_FF[9] == 1 & GEN_CDC_FIFO_FF[10] == 0);


wire SKIP_TRIGGER = TRIG_PULSE & !GEN_TRIG_PULSE;

always@(posedge CLK40)
    if(RST_SYNC | START_SYNC)
        SKIP_TRIG_COUNTER <= 0;
    else if(SKIP_TRIGGER)   // & SKIP_TRIG_COUNTER!=32'hffffffff ) //maybe allow overflow..
        SKIP_TRIG_COUNTER <= SKIP_TRIG_COUNTER + 1;


always@(posedge CLK40)
    if(RST_SYNC | START_SYNC)
        TRIG_ID <= 0; //32'h3fff-10;
    else if(GEN_TRIG_PULSE)
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
            .TRIG_ID(TRIG_ID_FF[30:0]),
			.N_BITS_TRIGGER_ID(CONF_N_BITS_TRIGGER_ID),
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
    
wire cdc_wfull;
wire [127:0] cdc_data;
wire fifo_full, cdc_fifo_empty;
wire cdc_fifo_write;
    
always@(posedge CLK40) begin
    if(RST_SYNC)
        LOST_DATA_CNT <= 0;
    else if (cdc_wfull && cdc_fifo_write && LOST_DATA_CNT != 8'hff)
        LOST_DATA_CNT <= LOST_DATA_CNT +1;
end

wire [7:0] LE [3:0];
// calculate relative distance of LE of input signals to LE of TRIG_PULSE (generation of trigger signal), fixed offset is needed for correct relative distance
//assign LE[0] = VALID[0] ? LAST_RISING_REL[0] + 16'd43 : 0;
assign LE[0] = VALID[0] ? LAST_RISING_REL[0][7:0] : 0;
assign LE[1] = VALID[1] ? LAST_RISING_REL[1][7:0] : 0;
assign LE[2] = VALID[2] ? LAST_RISING_REL[2][7:0] : 0;
assign LE[3] = VALID[3] ? LAST_RISING_REL[3][7:0] : 0;

///TODO: add some status? Lost count? Skipped triggers?
assign cdc_data = {TRIG_ID, TIME_STAMP, LE[3], LE[2], LE[1], LE[0]};
assign cdc_fifo_write = GEN_CDC_FIFO_PULSE;

wire [127:0] cdc_data_out;
cdc_syncfifo #(.DSIZE(128), .ASIZE(3)) cdc_syncfifo
(
    .rdata(cdc_data_out),
    .wfull(cdc_wfull),
    .rempty(cdc_fifo_empty),
    .wdata(cdc_data),
    .winc(cdc_fifo_write), .wclk(CLK40), .wrst(RST_SYNC),
    .rinc(!fifo_full), .rclk(BUS_CLK), .rrst(RST)
);

wire out_fifo_read;
wire [127:0] out_fifo_data_out;
wire out_fifo_empty;
gerneric_fifo #(.DATA_SIZE(128), .DEPTH(64))  gerneric_fifo
( 
    .clk(BUS_CLK), .reset(RST),
    .write(!cdc_fifo_empty),
    .read(out_fifo_read),
    .data_in(cdc_data_out),
    .full(fifo_full),
    .empty(out_fifo_empty),
    .data_out(out_fifo_data_out), .size()
);

reg [2:0] out_word_cnt;
assign out_fifo_read = (out_word_cnt==0 & !out_fifo_empty && FIFO_READ);

always@(posedge BUS_CLK)
    if(RST)
        out_word_cnt <= 0;
    else if (FIFO_READ)
        out_word_cnt <= out_word_cnt + 1;
    
reg [127:0] fifo_data_out_buf;
always@(posedge BUS_CLK)
    if(out_fifo_read)
        fifo_data_out_buf <= out_fifo_data_out;
        
wire [15:0]  fifo_data_out_word [7:0];
    
    
genvar iw;
generate
    assign fifo_data_out_word[0] = out_fifo_data_out[15:0];
    for (iw = 1; iw < 8; iw = iw + 1) begin: gen_out
         assign fifo_data_out_word[iw] = fifo_data_out_buf[(iw+1)*16-1:iw*16];
    end
endgenerate 

assign FIFO_DATA = fifo_data_out_word[out_word_cnt];
assign FIFO_EMPTY = out_word_cnt==0 & out_fifo_empty;

endmodule
