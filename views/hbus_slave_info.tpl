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
            %if slave.hbusSlaveHasAUTH:
                <li>Autenticação de Mestre</li>
            %end
            
            %if slave.hbusSlaveHasREVAUTH:
                <li>Autenticação reversa</li>
            %end
            
            %if slave.hbusSlaveHasEP:
                <li>Suporte a Endpoints</li>
            %end
            
            %if slave.hbusSlaveHasCRYPTO:
                <li>Criptografia para objetos</li>
            %end
            
            %if slave.hbusSlaveHasUCODE:
                <li>Microcódigo HBUS</li>
            %end
            
            %if slave.hbusSlaveHasINT:
                <li>Interrupções</li>
            %end
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
                <th scope="col">Tipo de dados</th>
                <th scope="col">Último valor conhecido</th>
                <th scope="col">Campos extras</th>
                <th scope="col">Controle</th>
            </tr>
        </thead>
        <tbody>
        
        %i = 1
        %for object in slave.hbusSlaveObjects.values():
        
            %if object.objectHidden:
                %continue
            %end
            
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
                <td>{{hbusSlaveObjectDataType.dataTypeNames[object.objectDataType]}}</td>
                
                %if object.objectLastValue == None:
                <td style="text-align: center">
                    %if object.objectPermissions != 2:
                        <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}">&mdash;</a>
                    %else:
                        &mdash;
                    %end
                </td>
                %else:
                    <td style="text-align: center"><a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}">{{object.getFormattedValue()}}</a></td>
                %end
                
                <td>
                    %if object.objectExtendedInfo != None:
                        {{object.objectExtendedInfo.keys()}}
                    %else:
                        &mdash;
                    %end
                </td>
                
                <td>
                    
                    %if object.objectPermissions != 1:
                    
                    %if object.objectDataType == hbusSlaveObjectDataType.dataTypeUnsignedInt:
                        %if object.objectDataTypeInfo in (hbusSlaveObjectDataType.dataTypeUintPercent,hbusSlaveObjectDataType.dataTypeUintLinPercent,hbusSlaveObjectDataType.dataTypeUintLogPercent):
                            <form action="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}" method="post">
                            <input type="range" name="value" min="0" max="100">
                                <button type="submit" class="positive" name="save">
                                <!-- <img src="/static/apply2.png" alt=""/> -->
                                Enviar
                                </button>
                            </form>
                        %else:
                            &mdash;
                        %end
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeByte:
                        %if object.objectDataTypeInfo == hbusSlaveObjectDataType.dataTypeByteBin:
                            <form action="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}" method="post">
                                
                                
                            </form>
                        %elif object.objectDataTypeInfo == hbusSlaveObjectDataType.dataTypeByteBool:
                            <form action="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}" method="post">
                            <input type="radio" name="value" value="ON">ON<br>
                            <input type="radio" name="value" value="OFF">OFF
                                <button type="submit" class="positive" name="save">
                                Enviar
                                </button>
                            </form>
                        %else:
                            &mdash;
                        %end
                    %else:
                        &mdash;
                    %end
                    
                    %else:
                        &mdash;
                    %end
                    
                </td>
                
            </tr>
            
            %i += 1
            
        %end
        
        </tbody>
        </table>
        
</html>
