
module tlu_tx ( 
    input wire SYS_CLK, CLK320, CLK160, SYS_RST, ENABLE, TRIG,
    input wire [14:0] TRIG_ID,
    output wire READY,
    input wire [3:0] TRIG_LE,
    input wire TLU_CLOCK, TLU_BUSY,
    output wire TLU_TRIGGER, TLU_RESET
);

localparam WAIT_STATE = 0, TRIG_STATE = 1, READ_ID_STATE = 2;

reg [1:0] state, state_next;
always@(posedge SYS_CLK)
    if(SYS_RST)
        state <= WAIT_STATE;
    else
        state <= state_next;

always@(*) begin
    state_next = state;
    
    case(state)
        WAIT_STATE: 
            if(TRIG)
                state_next = TRIG_STATE;
        TRIG_STATE:
            if(TLU_BUSY)
                state_next = READ_ID_STATE;
        READ_ID_STATE:
            if(!TLU_BUSY)
                state_next = WAIT_STATE;
        default : state_next = WAIT_STATE;
    endcase
end

reg [15:0] TRIG_ID_SR;
initial TRIG_ID_SR = 0;
always@(posedge TLU_CLOCK or posedge TRIG)
    if(TRIG)
        TRIG_ID_SR <= {TRIG_ID, 1'b0};
    else
        TRIG_ID_SR <= {1'b0, TRIG_ID_SR[15:1]};

reg TRIG_OUT;
always@(posedge SYS_CLK)
    TRIG_OUT = (state == TRIG_STATE) || (state_next == TRIG_STATE) || (TRIG_ID_SR[0] & TLU_BUSY);

assign TLU_RESET = 0;
assign READY = (state == WAIT_STATE && TLU_CLOCK != 1'b1) || !ENABLE;

reg [15:0] TRIG_DES;
wire [3:0] TRIG_LE_CALC;
assign TRIG_LE_CALC = TRIG_LE -1;

integer i;
always@(posedge SYS_CLK)
    for(i = 15; i>=0; i = i - 1)
        TRIG_DES[i] = (i <= TRIG_LE_CALC);

reg TRIG_FF;
always@(posedge SYS_CLK)
    TRIG_FF <= TRIG;
    
reg [1:0] trig_320_sr;
always@(posedge CLK320)
    trig_320_sr[1:0] <= {trig_320_sr[0], TRIG_FF};

wire LOAD_320;
assign LOAD_320 = (trig_320_sr[0] == 1 && trig_320_sr[1] == 0);

reg TRIG_OUT_320; 
always@(posedge CLK320)
    TRIG_OUT_320 <= TRIG_OUT;
    
reg [15:0] TRIG_DES_320;
always@(posedge CLK320)
    if(LOAD_320)
        TRIG_DES_320 <= TRIG_DES;
    else if (trig_320_sr[1])
        TRIG_DES_320 <= {TRIG_DES_320[13:0], 2'b11};
    else
        TRIG_DES_320[15:14] <= {2{TRIG_OUT_320}};
        
ODDR oddr(
    .D1(TRIG_DES_320[14]), .D2(TRIG_DES_320[15]), 
    .C(CLK320), .CE(1'b1), .R(1'b0), .S(1'b0),
    .Q(TLU_TRIGGER)
);

endmodule
