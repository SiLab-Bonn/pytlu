/**
 * ------------------------------------------------------------
 * Copyright (c) SILAB , Physics Institute of Bonn University 
 * ------------------------------------------------------------
 */

`timescale 1ps / 1ps

`include "firmware/src/tlu.v"
 
`include "seq_gen/seq_gen.v"
`include "seq_gen/seq_gen_core.v"
`include "utils/clock_multiplier.v"

`include "bram_fifo/bram_fifo_core.v"
`include "bram_fifo/bram_fifo.v"

`include "tlu/tlu_controller_core.v"
`include "tlu/tlu_controller_fsm.v"
`include "tlu/tlu_controller.v"

`include "tdc_s3/tdc_s3_core.v"
`include "tdc_s3/tdc_s3.v"

`include "utils/flag_domain_crossing.v"
`include "utils/3_stage_synchronizer.v"
`include "rrp_arbiter/rrp_arbiter.v"

//`include "CY7C1472V33.v"


module tb (
    input wire           BUS_CLK,
    input wire           BUS_RST,
    input wire   [31:0]  BUS_ADD,
    inout wire   [31:0]  BUS_DATA,
    input wire           BUS_RD,
    input wire           BUS_WR,
    output wire          BUS_BYTE_ACCESS,
    input wire           STREAM_READY,
    output wire          STREAM_WRITE,
    output wire [15:0]   STREAM_DATA

);

wire [15:0] ZEST_BUS_ADD;
assign ZEST_BUS_ADD = BUS_ADD[15:0] + 16'h2000;

wire [7:0] SEQ_OUT;
wire [5:0] DUT_TRIGGER, DUT_RESET, DUT_BUSY, DUT_CLOCK;
wire [3:0] BEAM_TRIGGER;
assign #100 BEAM_TRIGGER = SEQ_OUT[3:0];
wire [2:0] USB_STREAM_FLAGS_N;
wire USB_STREAM_FX2RDY;

wire SRAM_CLK;
wire [22:0] SRAM_ADD;
wire SRAM_ADV_LD_N;
wire [1:0] SRAM_BW_N;
wire [17:0] SRAM_DATA;
wire SRAM_OE_N;
wire SRAM_WE_N;

wire I2C_SDA_OUT;

wire USB_STREAM_CLK;
assign USB_STREAM_CLK = BUS_CLK;
wire USB_STREAM_SLWR_n;
assign STREAM_WRITE = !USB_STREAM_SLWR_n;
    
tlu dut (
        .BUS_CLK_IN(BUS_CLK),
        .USB_BUS_ADD(ZEST_BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_OE_N(!BUS_RD),
        .BUS_RD_N(!BUS_RD),
        .BUS_WR_N(!BUS_WR),
        .BUS_CS_N(!(BUS_RD || BUS_WR)),
        
        
        .BEAM_TRIGGER(BEAM_TRIGGER),
        .I2C_SDA_OUT(I2C_SDA_OUT),
        
        .DUT_TRIGGER(DUT_TRIGGER), .DUT_RESET(DUT_RESET), 
        .DUT_BUSY(DUT_BUSY), .DUT_CLOCK(DUT_CLOCK),
        
        .USB_STREAM_CLK(USB_STREAM_CLK),
        .USB_STREAM_FLAGS_N(USB_STREAM_FLAGS_N),
        .USB_STREAM_FX2RDY(USB_STREAM_FX2RDY),
        .USB_STREAM_SLWR_n(USB_STREAM_SLWR_n),
        .USB_STREAM_DATA(STREAM_DATA),
        
        .SRAM_CLK(SRAM_CLK),
        .SRAM_ADD(SRAM_ADD),
        .SRAM_ADV_LD_N(SRAM_ADV_LD_N),
        .SRAM_BW_N(SRAM_BW_N),
        .SRAM_DATA(SRAM_DATA),
        .SRAM_OE_N(SRAM_OE_N),
        .SRAM_WE_N(SRAM_WE_N)
        
);   
assign I2C_SDA_OUT = 1'b0;
    
assign USB_STREAM_FLAGS_N[1] = STREAM_READY;
assign USB_STREAM_FX2RDY = 1;

assign BUS_BYTE_ACCESS = BUS_ADD < 32'h8000_0000 ? 1'b1 : 1'b0;

localparam SEQ_GEN_BASEADDR = 32'hc000;
localparam SEQ_GEN_HIGHADDR = 32'hf000-1;
    
localparam TLU_BASEADDR = 32'hf000;
localparam TLU_HIGHADDR = 32'hf100-1;

localparam FIFO_BASEADDR = 32'hf100;
localparam FIFO_HIGHADDR = 32'hf200-1;

localparam TDC_BASEADDR = 32'hf200;
localparam TDC_HIGHADDR = 32'hf300 - 1;
    
localparam FIFO_BASEADDR_DATA = 32'h8000_0000;
localparam FIFO_HIGHADDR_DATA = 32'h9000_0000;
        
localparam ABUSWIDTH = 32;
assign BUS_BYTE_ACCESS = BUS_ADD < 32'h8000_0000 ? 1'b1 : 1'b0;


wire CLK640;
clock_multiplier #( .MULTIPLIER(2) ) i_clock_multiplier_two(.CLK(dut.CLK320),.CLOCK(CLK640)); 

seq_gen 
#( 
    .BASEADDR(SEQ_GEN_BASEADDR), 
    .HIGHADDR(SEQ_GEN_HIGHADDR),
    .ABUSWIDTH(ABUSWIDTH),
    .MEM_BYTES(8*1024), 
    .OUT_BITS(8) 
) i_seq_gen
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .SEQ_EXT_START(1'b0),
    .SEQ_CLK(CLK640),
    .SEQ_OUT(SEQ_OUT)
);

wire ACKNOWLEDGE;
wire TLU_FIFO_READ;
wire TLU_FIFO_EMPTY;
wire [31:0] TLU_FIFO_DATA;

assign TLU_FIFO_READ = 1;
    
tlu_controller #(
    .BASEADDR(TLU_BASEADDR),
    .HIGHADDR(TLU_HIGHADDR),
    .ABUSWIDTH(ABUSWIDTH),
    .DIVISOR(4),
    .TLU_TRIGGER_MAX_CLOCK_CYCLES(16)
) i_tlu_controller (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    
    .TRIGGER_CLK(dut.CLK40),
    
    .FIFO_READ(TLU_FIFO_READ),
    .FIFO_EMPTY(TLU_FIFO_EMPTY),
    .FIFO_DATA(TLU_FIFO_DATA),
    
    .FIFO_PREEMPT_REQ(),
    
    .TRIGGER({7'b0, DUT_TRIGGER[0]}),
    .TRIGGER_VETO({7'b0, 1'b1}),
    
    .TLU_TRIGGER(DUT_TRIGGER[0]),
    .TLU_RESET(DUT_RESET[0]),
    .TLU_BUSY(DUT_BUSY[0]),
    .TLU_CLOCK(DUT_CLOCK[0]),
    
    .EXT_TRIGGER_ENABLE(1'b1),
    .TRIGGER_ACKNOWLEDGE(ACKNOWLEDGE),
    .TRIGGER_ACCEPTED_FLAG(ACKNOWLEDGE),
    
    .TIMESTAMP()
);

wire TDC_FIFO_READ;
wire TDC_FIFO_EMPTY;
wire [31:0] TDC_FIFO_DATA;
wire TDC_IN;
assign #100 TDC_IN = DUT_TRIGGER[0];
    
tdc_s3 #(
    .BASEADDR(TDC_BASEADDR),
    .HIGHADDR(TDC_HIGHADDR),
    .ABUSWIDTH(ABUSWIDTH),
    .CLKDV(4),
    .DATA_IDENTIFIER(4'b0000),
    .FAST_TDC(1),
    .FAST_TRIGGER(1)
) i_tdc (
    .CLK320(dut.CLK320),
    .CLK160(dut.CLK160),
    .DV_CLK(dut.CLK40),
    .TDC_IN(TDC_IN),
    .TDC_OUT(),
    .TRIG_IN(BEAM_TRIGGER[0]),
    .TRIG_OUT(),
    
    .FIFO_READ(TDC_FIFO_READ),
    .FIFO_EMPTY(TDC_FIFO_EMPTY),
    .FIFO_DATA(TDC_FIFO_DATA),
    
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    
    .ARM_TDC(1'b0),
    .EXT_EN(1'b0),
    
    .TIMESTAMP(16'b0)
    );
    
    
wire ARB_READY_OUT, ARB_WRITE_OUT;
wire [31:0] ARB_DATA_OUT;

rrp_arbiter
#(
    .WIDTH(2)
) rrp_arbiter
(
    .RST(BUS_RST),
    .CLK(BUS_CLK),

    .WRITE_REQ({!TDC_FIFO_EMPTY, !TLU_FIFO_EMPTY}),
    .HOLD_REQ({2'b0}),
    .DATA_IN({TDC_FIFO_DATA, TLU_FIFO_DATA}),
    .READ_GRANT({TDC_FIFO_READ, TLU_FIFO_READ}),

    .READY_OUT(ARB_READY_OUT),
    .WRITE_OUT(ARB_WRITE_OUT),
    .DATA_OUT(ARB_DATA_OUT)
    );
    

bram_fifo 
#(
    .BASEADDR(FIFO_BASEADDR),
    .HIGHADDR(FIFO_HIGHADDR),
    .BASEADDR_DATA(FIFO_BASEADDR_DATA),
    .HIGHADDR_DATA(FIFO_HIGHADDR_DATA),
    .ABUSWIDTH(ABUSWIDTH)
) i_out_fifo (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    
    .FIFO_READ_NEXT_OUT(ARB_READY_OUT),
    .FIFO_EMPTY_IN(!ARB_WRITE_OUT),
    .FIFO_DATA(ARB_DATA_OUT),

    .FIFO_NOT_EMPTY(),
    .FIFO_FULL(),
    .FIFO_NEAR_FULL(),
    .FIFO_READ_ERROR()
    );
    

//cy1472 cy1472( .d(SRAM_DATA), .clk(SRAM_CLK), .a(SRAM_ADD[21:0]), .bws(SRAM_BW_N), 
//            .we_b(SRAM_WE_N), .adv_lb(SRAM_ADV_LD_N), .ce1b(1'b0), .ce2(1'b1), 
//            .ce3b(1'b0), .oeb(SRAM_OE_N), .cenb(1'b0), .mode(1'b0));
    

reg [17:0] sram [8388608-1:0];
reg [1:0] op_q;
reg [22:0] addr1, addr2;
reg [17:0] data1, data2;
always@(posedge SRAM_CLK) begin
    op_q <= {op_q[0], SRAM_WE_N};

    addr1 <= SRAM_ADD;
    addr2 <= addr1;

    data1 <= sram[SRAM_ADD];
    data2 <= data1;
    
    if(op_q[1] == 1'b0)
        sram[addr2] <= SRAM_DATA;
end

assign SRAM_DATA = (op_q[1]==0) ? 18'bz: data2;

    
initial begin
    
    $dumpfile("/tmp/tlu.vcd");
    $dumpvars(0);

end

endmodule
