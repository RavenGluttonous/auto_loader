---
type: "always_apply"
---

2.接口交互方式
	东华医为科技有限公司与第三方PACS系统采用WebService+XML的接口方式进行数据交互。

交互接口说明：
功能说明	根据交互操作服务编码和具体的消息流进行相应的交互操作
通讯方式	WebService+Xml
服务地址	https://192.168.206.193:1443/csp/hsb/DHC.Published.PISWebService.BS.PISWebService.CLS?WSDL=1
方法名	HIPMessageServer(入参1 input1,入参2 input2)
	1、action类型为字符串，服务编号传给该参数
    2、message类型为标准消息请求流传给该参数

申明：所有服务中“示例”仅用于说明Xml的总体结构，具体到每个字段的属性名以“请求消息”、“应答消息”定义中为准。



5.4病理闭环状态变更回传（必须）
病理闭环状态变更回传
接口方式	XML+WebService
服务编码	MES0167
服务名称	状态变更回传HIS
服务提供者	平台
服务调用者	第三方系统
调用时机	当检查状态节点发生变化时调用

请求消息：
代码	名称	数据类型	约束	说明
SourceSystem	系统代码	varchar(20)	必填	总线接入系统代码
MessageID	消息id	varchar(100)		
StatusParameter     （1..N）
PATPatientID	患者登记号	varchar(100)		
PAADMVisitNumber	患者就诊号	varchar(100)	必填	
OEORIOrderItemID	医嘱id	varchar(100)	条件必填	检验检查闭环必填
OEORIOrdExecID	医嘱执行记录id	varchar(100)	条件必填	口服药、静配闭环必填
SpecimenID	检验条码号/标本号	varchar(100)	条件必填	检验闭环，生成条码号后必填
RISRExamID	检查号	varchar(100)	条件必填	检查闭环，登记产生检查号后必填
RISRSystemType	系统类型	varchar(50)	条件必填	附录一：系统代码
Position	检查部位	varchar(200)		多部位时将多个部位以@@分隔
OperAppID	手术申请id	varchar(100)	条件必填	手术闭环必填
BloodAppID	输血申请id	varchar(100)	条件必填	输血闭环必填
BloodBagNo	用血血袋号	varchar(100)	条件必填	输血分配血袋后必填
ConsultAppID	会诊申请id	varchar(100)	条件必填	会诊闭环必填
StatusCode	状态代码	varchar(10)	必填	附录一：状态代码
UpdateUserCode	更新人工号	varchar(50)	必填	
UpdateUserName	更新人姓名	varchar(50)	必填	
UpdateDateTime	更新日期时间	varchar(20)	必填	yyyy-mm-dd hh24:mi:ss
ESOperateDeptCode	操作科室代码	Varchar(50)		
ESOperateDept	操作科室名称	Varchar(50)		
ESReportID	报告号	Varchar(50)		报告号

示例



<Request>
	<Header>
		<SourceSystem>02</SourceSystem>
		<MessageID>yb2505172</MessageID>
	</Header>
	<Body>
		<StatusParameter>
			<PATPatientID>0000155243</PATPatientID>
			<PAADMVisitNumber>20235202</PAADMVisitNumber>
			<OEORIOrderItemID>15244778||425</OEORIOrderItemID>
			<OEORIOrdExecID/>
			<SpecimenID/>
			<RISRExamID>yb2505172</RISRExamID>
			<RISRSystemType>PIS</RISRSystemType>
			<Position/>
			<OperAppID/>
			<BloodAppID/>
			<BloodBagNo/>
			<ConsultAppID/>
			<StatusCode>RP</StatusCode>
			<UpdateUserCode>郭昌容</UpdateUserCode>
			<UpdateUserName>郭昌容</UpdateUserName>
			<UpdateDateTime>2025-12-01 16:46:33</UpdateDateTime>
		</StatusParameter>
	</Body>
</Request>
应答消息：
代码	名称	数据类型	是否必输	备注
SourceSystem	消息来源	VARCHAR(50)	NOT NULL	
MessageID	消息ID	VARCHAR(30)	NOT NULL	
ResultCode	响应码	VARCHAR(6)	NOT NULL	0：成功 -1:失败
ResultContent	响应信息	VARCHAR(300)	NOT NULL	
示例
<Response>
	<Header>
		<SourceSystem></SourceSystem>
		<MessageID></MessageID>
	</Header>
	<Body>
		<ResultCode>0</ResultCode>
		<ResultContent>成功</ResultContent>
	</Body>
</Response>

