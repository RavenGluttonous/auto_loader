import requests

from hospital_info import data_processing
from utils import http_request, logger


class StatusChangeClient:
    """病理闭环状态变更回传（MES0167） WebService 客户端封装。

    按照东华接口文档，通过 SOAP + HIPMessageServer(input1,input2) 调用：
    - input1: 服务编码 MES0167
    - input2: CDATA 包裹的 <Request>...</Request> XML
    """

    def __init__(
        self,
        service_url: str = "https://192.168.206.193:1443/csp/hsb/DHC.Published.PISWebService.BS.PISWebService.CLS",
        service_code: str = "MES0167",  # 状态变更回传服务编码
    ) -> None:
        self.service_url = service_url
        self.service_code = service_code

    def send_status_change(
        self,
        message_id: str,
        source_system: str,
        status_params: list[dict],
    ) -> bool:
        """发送 1..N 条状态变更请求。

        Args:
            message_id: 消息ID，对应文档中的 MessageID。
            source_system: 系统代码，对应文档中的 SourceSystem。
            status_params: 每个元素为一个 dict，对应一个 <StatusParameter>，
                预期 key 包括（均为字符串，可为空）：
                - PATPatientID
                - PAADMVisitNumber
                - OEORIOrderItemID
                - OEORIOrdExecID
                - SpecimenID
                - RISRExamID
                - RISRSystemType
                - Position
                - OperAppID
                - BloodAppID
                - BloodBagNo
                - ConsultAppID
                - StatusCode
                - UpdateUserCode
                - UpdateUserName
                - UpdateDateTime
                - ESOperateDeptCode
                - ESOperateDept
                - ESReportID

        Returns:
            True 表示调用成功且 ResultCode == "0"，否则返回 False。
        """

        if not status_params:
            logger.warning("StatusChangeClient.send_status_change 调用时 status_params 为空，跳过发送")
            return False

        # 组装多个 <StatusParameter> 节点
        sp_xml_list: list[str] = []
        for sp in status_params:
            sp = sp or {}
            sp_xml_list.append(
                f"""<StatusParameter>
            <PATPatientID>{sp.get('PATPatientID', '')}</PATPatientID>
            <PAADMVisitNumber>{sp.get('PAADMVisitNumber', '')}</PAADMVisitNumber>
            <OEORIOrderItemID>{sp.get('OEORIOrderItemID', '')}</OEORIOrderItemID>
            <OEORIOrdExecID>{sp.get('OEORIOrdExecID', '')}</OEORIOrdExecID>
            <SpecimenID>{sp.get('SpecimenID', '')}</SpecimenID>
            <RISRExamID>{sp.get('RISRExamID', '')}</RISRExamID>
            <RISRSystemType>{sp.get('RISRSystemType', '')}</RISRSystemType>
            <Position>{sp.get('Position', '')}</Position>
            <OperAppID>{sp.get('OperAppID', '')}</OperAppID>
            <BloodAppID>{sp.get('BloodAppID', '')}</BloodAppID>
            <BloodBagNo>{sp.get('BloodBagNo', '')}</BloodBagNo>
            <ConsultAppID>{sp.get('ConsultAppID', '')}</ConsultAppID>
            <StatusCode>{sp.get('StatusCode', '')}</StatusCode>
            <UpdateUserCode>{sp.get('UpdateUserCode', '')}</UpdateUserCode>
            <UpdateUserName>{sp.get('UpdateUserName', '')}</UpdateUserName>
            <UpdateDateTime>{sp.get('UpdateDateTime', '')}</UpdateDateTime>
            <ESOperateDeptCode>{sp.get('ESOperateDeptCode', '')}</ESOperateDeptCode>
            <ESOperateDept>{sp.get('ESOperateDept', '')}</ESOperateDept>
            <ESReportID>{sp.get('ESReportID', '')}</ESReportID>
        </StatusParameter>"""
            )

        status_parameters_xml = "".join(sp_xml_list)

        # 内部业务 XML：<Request> 结构
        request_xml = f"""<Request>
    <Header>
        <SourceSystem>{source_system}</SourceSystem>
        <MessageID>{message_id}</MessageID>
    </Header>
    <Body>
{status_parameters_xml}
    </Body>
</Request>"""

        # SOAP Envelope，调用 HIPMessageServer(input1,input2)
        soap_envelope = f"""<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dhcc=\"http://www.dhcc.com.cn\">
   <soapenv:Header/>
   <soapenv:Body>
      <dhcc:HIPMessageServer>
         <dhcc:input1>{self.service_code}</dhcc:input1>
         <dhcc:input2><![CDATA[{request_xml}]]></dhcc:input2>
      </dhcc:HIPMessageServer>
   </soapenv:Body>
</soapenv:Envelope>"""

        headers = {"Content-Type": "text/xml; charset=utf-8"}

        try:
            resp = http_request.get_response(
                "POST",
                self.service_url,
                1,
                3,
                verify=False,
                headers=headers,
                data=soap_envelope,
            )
        except requests.RequestException as e:
            logger.error(f"调用状态变更回传接口异常: {e}")
            return False

        if resp is None:
            logger.error("调用状态变更回传接口失败，响应为空")
            return False

        try:
            xml_dict = data_processing.xml_to_dict(resp.text)
        except Exception as e:
            logger.error(
                f"解析状态变更回传接口返回XML失败: {e}, 原始内容: {resp.text[:500]}"
            )
            return False

        body = xml_dict.get("Response", {}).get("Body", {})
        result_code = str(body.get("ResultCode", "")).strip()
        result_content = body.get("ResultContent", "")
        if result_code == "0":
            logger.info(f"状态变更回传成功: {result_content}")
            return True
        else:
            logger.error(f"状态变更回传失败: {result_code} {result_content}")
            return False
