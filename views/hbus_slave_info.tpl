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
        <h3>{{slave.hbusSlaveDescription}} &lt;{{hex(slave.hbusSlaveUniqueDeviceInfo)}}&gt; @ {{slave.hbusSlaveAddress.hbusAddressBusNumber}}:{{slave.hbusSlaveAddress.hbusAddressDevNumber}}</h3>
    </div>
    
    <div>
        <h4>Capacidades do dispositivo</h4>
        
        <ul>
        
        </ul>
        
    </div>
    
    <div>
        <h4>Objetos do dispositivo</h4>
    </div>
    
    <table id="hor-minimalist-a" summary="Lista de dispositivos ativos" style="margin-left: auto;margin-right: auto">
        <thead>
            <tr>
                <th scope="col">ID do objeto</th>
                <th scope="col">Descrição</th>
                <th scope="col">Permissões</th>
                <th scope="col">Tamanho em bytes</th>
                <th scope="col">Último valor conhecido</th>
            </tr>
        </thead>
        <tbody>
        
        %i = 1
        %for object in slave.hbusSlaveObjects.values():
            
            <tr>
                <td style="text-align: center">{{i}}</td>
                <td>{{object.objectDescription}}</td>
                <td style="text-align: center">
                %if object.objectPermissions == 1:
                    R
                %elif object.objectPermissions == 2:
                    W
                %else:
                    RW
                %end
                </td>
                <td style="text-align: center">{{object.objectSize}}</td>
                
                %if object.objectLastValue == None:
                <td style="text-align: center">
                    %if object.objectPermissions != 2:
                        <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}">&mdash;</a>
                    %else:
                        &mdash;
                    %end
                </td>
                %else:
                    <td style="text-align: center"><a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}">{{object.objectLastValue}}</a></td>
                %end
            </tr>
            
            %i += 1
            
        %end
        
        </tbody>
        </table>
        
</html>
