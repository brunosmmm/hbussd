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

<div class="hbusContainer">

    <header class="hbusMHeader">
        <section>
            <a href="/" class="hbusLogo">HBUS</a>
        </section>
        <aside>
            <div class="hbusStatus">
                
                <div class = "activeSlaveCount">{{masterStatus.activeSlaveCount}}</div>
                <div class = "statusText">Dispositivos <br /> ativos</div>
                
            </div>
            
            <div class="hbusStatus">
                
            </div>
        </aside>
    </header>
    
    <section class="hbusDeviceDescription">
        <a class="left" href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}">{{slave.hbusSlaveDescription}}</a>
        <div class="right">&lt;{{hex(slave.hbusSlaveUniqueDeviceInfo)}}&gt; @ {{slave.hbusSlaveAddress.hbusAddressBusNumber}}:{{slave.hbusSlaveAddress.hbusAddressDevNumber}}</div>
    </section>
    
    <div class="hbusMMain">
        
        %if readObjCount > 0:
        
        <section class="readObjects">
        
            <ul class="objGrid">
                
                %i = 1
                %for object in slave.hbusSlaveObjects.values():
                
                    %if object.objectHidden:
                        %continue
                    %end
                    
                    %if object.objectLevel < objectLevel:
                        %continue
                    %end
                    
                    %if object.objectPermissions == 2:
                        %continue
                    %end
                    
                    
                    %if object.objectDataType == hbusSlaveObjectDataType.dataTypeByte:
                    
                        %if object.objectDataTypeInfo == hbusSlaveObjectDataType.dataTypeByteBool:
                        
                            <li class="boolsw">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}">{{object.objectDescription}}</a>
                                <div class="hbusObjectValue">
                                    %if object.objectLastValue == None:
                                        ?
                                    %else:
                                        {{object.getFormattedValue()}}
                                    %end
                                </div>
                            </li>
                            
                        %else:
                        
                            <li class="byte"><a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}">{{object.objectDescription}}</a></li>
                        
                        %end
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeUnsignedInt:
                    
                        %if object.objectDataTypeInfo in [hbusSlaveObjectDataType.dataTypeUintPercent,hbusSlaveObjectDataType.dataTypeUintLogPercent,hbusSlaveObjectDataType.dataTypeUintLinPercent]:
                        
                            <li class="percent"><a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/{{i}}">{{object.objectDescription}}</a></li>
                        
                        %else:
                        
                            %pass
                        
                        %end
                    
                    %end
                    %i += 1
                    
               %end
                
            </ul>
        
        </section>
        
        %end
        
        %if writeObjCount > 0:
        
        <section class="writeObjects">
        
            <ul class="objGrid">
                
                %i = 1
                %for object in slave.hbusSlaveObjects.values():
                
                    %if object.objectHidden:
                        %continue
                    %end
                    
                    %if object.objectLevel < objectLevel:
                        %continue
                    %end
                    
                    %if object.objectPermissions == 1:
                        %continue
                    %end
                    
                    
                    %if object.objectDataType == hbusSlaveObjectDataType.dataTypeByte:
                    
                        %if object.objectDataTypeInfo == hbusSlaveObjectDataType.dataTypeByteBool:
                        
                            <li class="boolsw"><a href="#">{{object.objectDescription}}</a></li>
                            
                        %else:
                        
                            <li class="byte"><a href="#">{{object.objectDescription}}</a></li>
                        
                        %end
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeUnsignedInt:
                    
                        %if object.objectDataTypeInfo in [hbusSlaveObjectDataType.dataTypeUintPercent,hbusSlaveObjectDataType.dataTypeUintLogPercent,hbusSlaveObjectDataType.dataTypeUintLinPercent]:
                        
                            <li class="percent"><a href="#">{{object.objectDescription}}</a></li>
                        
                        %else:
                        
                            %pass
                        
                        %end
                    
                    %end
                    %i += 1
                    
               %end
                
            </ul>
        
        </section>
        
        %end
    <!--
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
            
            %if object.objectLevel < objectLevel:
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
    -->
        
    </div>
    
</div>
        
</html>
