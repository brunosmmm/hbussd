<!DOCTYPE html>
<html>
    <head>
        <title>HBUS Server</title>
        <style type="text/css">
        <!--
        @import url("/static/style.css");
        -->
        </style>
        
        <meta name="viewport" content="user-scalable=no" />
        <link rel="apple-touch-icon" href="/static/apple-touch-icon.png"/>
        <link rel="apple-touch-icon-precomposed" href="/static/apple-touch-icon-precomposed.png"/>
        
    </head>

<div class="hbusContainer">

<div class="hbusTopContainer">

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
                <div class="statusText"><a href="/bus/{{slave.hbusSlaveAddress.hbusAddressBusNumber}}">BUS {{slave.hbusSlaveAddress.hbusAddressBusNumber}}</a></div>
            </div>
        </aside>
    </header>
    
    <section class="hbusDeviceDescription">
        <a class="left" href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}">{{slave.hbusSlaveDescription}}</a>
        <div class="right">Objeto {{objectNumber}}</div>
    </section>
    
</div>
    
    <div class="hbusMMain">
        
            <ul class="objSetGrid">
                    
                    %object = slave.hbusSlaveObjects[objectNumber]
                    
                    %if object.objectPermissions == 2:
                        %canRead = False
                    %else:
                        %canRead = True
                    %end
                    
                    %if object.objectDataType == hbusSlaveObjectDataType.dataTypeByte:
                    
                        %if object.objectDataTypeInfo == hbusSlaveObjectDataType.dataTypeByteBool:
                        
                            <li class="boolsw">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/setget-{{objectNumber}}">
                                    <p>{{object.objectDescription}}</p>
                                    %if canRead:                               
                                    <span class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                    
                                </a>
                            </li>
                            
                            <li class="onoff">
                                
                                <p class = "objControlText">Controles</p>
                                
                                <form action="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/set-{{objectNumber}}" method="post">
                                    <button type="submit" class="objSetButton onoff" name="value" value="ON">
                                        ON
                                    </button>
                                    <button type="submit" class="objSetButton onoff" name="value" value="OFF">
                                        OFF
                                    </button>
                                </form>
                            </li>
                            
                        %else:
                        
                            <li class="byte">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/setget-{{objectNumber}}">
                                    <p>{{object.objectDescription}}</p>
                                    %if canRead:
                                    <span class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                </a>
                            </li>
                        
                        %end
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeUnsignedInt:
                    
                        %if object.objectDataTypeInfo in [hbusSlaveObjectDataType.dataTypeUintPercent,hbusSlaveObjectDataType.dataTypeUintLogPercent,hbusSlaveObjectDataType.dataTypeUintLinPercent]:
                        
                            <li class="percent">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/setget-{{objectNumber}}">
                                    <p>{{object.objectDescription}}</p>
                                    %if canRead:
                                    <span class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                </a>
                            </li>
                            
                            <li class="setPercent">
                              
                                <p class = "objControlText">Controles</p>
                                
                                <form action="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/set-{{objectNumber}}" method="post">
                                    
                                    <div class="objectControlData">
                                        <span id="percentValue">{{percentToRange(object.getFormattedValue())}}</span>
                                        <span>%</span>
                                    </div>
                                    
                                    <input type="range" name="value" min="0" max="100" class="slider100" 
                                        value="{{percentToRange(object.getFormattedValue())}}" onchange="updPercent(this.value)" />
                                    <button type="submit" class="objSetButton" name="save">
                                        Aplicar
                                    </button>
                                </form>
                                
                                <script type="text/javascript">
                                    function updPercent(newValue) {
                                        document.getElementById("percentValue").innerHTML=newValue;
                                    }
                                </script>
                                
                            </li>
                        
                        %else:
                        
                            <li class="empty">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/setget-{{objectNumber}}">
                                    <p>{{object.objectDescription}}</p>
                                    %if canRead:
                                    <span class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                </a>
                            </li>
                        
                        %end
                        
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeInt:
                    
                            <li class="empty">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/setget-{{objectNumber}}">
                                    <p>{{object.objectDescription}}</p>
                                    %if canRead:
                                    <span class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                </a>
                            </li>
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeFixedPoint:
                    
                            <li class="empty">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/setget-{{objectNumber}}">
                                    <p>{{object.objectDescription}}</p>
                                    %if canRead:
                                    <span class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                </a>
                            </li>
                    
                    %end
                
            </ul>
        
    </div>
    
</div>
        
</html>
