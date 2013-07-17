<!DOCTYPE html>
<html>
	<head>
		<title>HBUS Server</title>
		<style type="text/css">
        <!--
        @import url("/static/style.css");
        -->
        </style>
	</head>

	<div>
		<h1><a href="/">HBUS Server</a></h1>
	</div>
	
	<div>
	   <h3>Dispositivos Ativos ({{len(slaves)}})</h3>
	</div>
	
    <table id="hor-minimalist-a" summary="Lista de dispositivos ativos" style="margin-left: auto;margin-right: auto">
        <thead>
            <tr>
                <th scope="col">Número do barramento</th>
                <th scope="col">Endereço</th>
                <th scope="col">Nome informado</th>
                <th scope="col">Número de objetos</th>
                <th scope="col">ID único</th>
            </tr>
        </thead>
        <tbody>
        
            %for slave in slaves:
                
                %if slave.basicInformationRetrieved == False:
                    %continue
                %end
                
                <tr>
                    <td style="text-align: center">{{slave.hbusSlaveAddress.hbusAddressBusNumber}}</td>
                    <td style="text-align: center">{{slave.hbusSlaveAddress.hbusAddressDevNumber}}</td>
                    <td>{{slave.hbusSlaveDescription}}</td>
                    <td style="text-align: center">{{len(slave.hbusSlaveObjects.values())}}</td>
                    <td><a href="slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}">{{hex(slave.hbusSlaveUniqueDeviceInfo)}}</a></td>
                </tr>
            
            %end
        
        </tbody>
        </table>
        
</html>