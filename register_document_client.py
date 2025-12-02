import requests

from hospital_info import data_processing
from utils import http_request, logger


class RegisterDocumentClient:
    """文档注册(RegisterDocument) WebService 客户端封装"""

    def __init__(
        self,
        service_url: str = "https://192.168.206.193:1443/csp/hsb/DHC.Published.PISWebService.BS.PISWebService.CLS",
        service_code: str = "MES0017",  # 文档注册服务编码
    ) -> None:
        self.service_url = service_url
        self.service_code = service_code

    def register_document(
        self,
        message_id: str,
        organization_code: str,
        pat_patient_id: str,
        pat_patient_name: str,
        paadm_visit_number: str,
        specimen_id: str,
        oeori_order_item_id: str,
        document_type: str,
        document_id: str,
        document_content_base64: str,
        document_path: str,
        document_pic_path: str,
        update_user_code: str,
        update_date: str,
        update_time: str,
        source_system: str = "AutoLoader",
    ) -> bool:
        """调用文档注册接口。

        返回 True 表示 ResultCode == "0"。
        """

        # 内部业务 XML，请求结构与东华《文档注册》接口文档一致
        request_xml = f"""<Request>
    <Header>
        <SourceSystem>{source_system}</SourceSystem>
        <MessageID>{message_id}</MessageID>
    </Header>
    <Body>
        <RegisterDocumentRt>
            <OrganizationCode>{organization_code}</OrganizationCode>
            <PATPatientID>{pat_patient_id}</PATPatientID>
            <PATPatientName>{pat_patient_name}</PATPatientName>
            <PAADMVisitNumber>{paadm_visit_number}</PAADMVisitNumber>
            <RISRExamID></RISRExamID>
            <SpecimenID>{specimen_id}</SpecimenID>
            <OEORIOrderItemID>{oeori_order_item_id}</OEORIOrderItemID>
            <DocumentType>{document_type}</DocumentType>
            <DocumentID>{document_id}</DocumentID>
            <DocumentContent>{document_content_base64}</DocumentContent>
            <DocumentPath>{document_path}</DocumentPath>
            <DocumentPicPath>{document_pic_path}</DocumentPicPath>
            <UpdateUserCode>{update_user_code}</UpdateUserCode>
            <UpdateDate>{update_date}</UpdateDate>
            <UpdateTime>{update_time}</UpdateTime>
        </RegisterDocumentRt>
    </Body>
</Request>"""

        # 按 MES0201 的 SoapUI 示例，文档注册同样通过 SOAP Envelope 调用 HIPMessageServer
        soap_envelope = f"""<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dhcc=\"http://www.dhcc.com.cn\">
   <soapenv:Header/>
   <soapenv:Body>
      <dhcc:HIPMessageServer>
         <dhcc:input1>{self.service_code}</dhcc:input1>
         <dhcc:input2><![CDATA[{request_xml}]]></dhcc:input2>
      </dhcc:HIPMessageServer>
   </soapenv:Body>
</soapenv:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            # SOAP 1.1 规范要求的 SOAPAction 头，按命名空间 + 方法名约定
            # 与对方 SoapUI 示例保持一致，使用 "http://www.dhcc.com.cn/HIPMessageServer"
            "SOAPAction": "\"http://www.dhcc.com.cn/HIPMessageServer\"",
        }

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
            logger.error(f"调用文档注册接口异常: {e}")
            return False

        if resp is None:
            logger.error("调用文档注册接口失败，响应为空")
            return False

        try:
            response_node = data_processing.parse_dhcc_hip_response(resp.text)
        except Exception as e:
            logger.error(
                f"解析文档注册接口返回XML失败: {e}, 原始内容: {resp.text[:500]}"
            )
            return False

        if not response_node:
            logger.error(
                f"解析文档注册接口返回XML失败: 未能解析到<Response>节点, 原始内容: {resp.text[:500]}"
            )
            return False

        body = response_node.get("Body", {})
        result_code = str(body.get("ResultCode", "")).strip()
        result_content = body.get("ResultContent", "")
        if result_code == "0":
            logger.info(f"文档注册成功: {result_content}")
            return True
        else:
            logger.error(f"文档注册失败: {result_code} {result_content}")
            return False
