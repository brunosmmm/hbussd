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
        
        <script type="text/javascript" src="/static/jquery-2.0.3.min.js" ></script>
        <link rel="stylesheet" href="/static/normalize.css">
        
        <script type="text/javascript">
        //LÊ DADOS DE OBJETO ATRAVÉS DE AJAX
            function loadObject(objectNumber)
            {
            var xmlhttp;
            var ID = objectNumber;
            
            if (window.XMLHttpRequest)
              {// code for IE7+, Firefox, Chrome, Opera, Safari
              xmlhttp=new XMLHttpRequest();
              }
            else
              {// code for IE6, IE5
              xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
              }
            xmlhttp.onreadystatechange=function()
              {
              if (xmlhttp.readyState==4 && xmlhttp.status==200)
                {
                document.getElementById("OVAL-"+ID).innerHTML=xmlhttp.responseText;
                }
              }
            xmlhttp.open("GET","/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/objdata-"+objectNumber,true);
            xmlhttp.send();
            }
        </script> 
        
        <script>
            //jQuery AJAX
            function loadObject2(objectNumber)
            {
                $("#OVAL-"+objectNumber).load("/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/objdata-"+objectNumber);
            }
            
        </script>
        
        
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
                <div class="statusText"><a href="/bus/{{slave.hbusSlaveAddress.bus_number}}">BUS {{slave.hbusSlaveAddress.bus_number}}</a></div>
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
                    
                    %if object.permissions == 2:
                        %canRead = False
                    %else:
                        %canRead = True
                    %end
                    
                    %if object.objectDataType == hbusSlaveObjectDataType.type_byte:
                    
                        %if object.objectDataTypeInfo == hbusSlaveObjectDataType.dataTypeByteBool:
                        
                            <li class="boolsw">
                                <a onclick="loadObject2({{objectNumber}})">
                                    <p>{{object.description}}</p>
                                    %if canRead:                               
                                    <span id="OVAL-{{objectNumber}}" class="hbusObjectValue">
                                        %if object.last_value == None:
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
                                <a onclick="loadObject({{objectNumber}})">
                                    <p>{{object.description}}</p>
                                    %if canRead:
                                    <span id="OVAL-{{objectNumber}}" class="hbusObjectValue">
                                        %if object.last_value == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                </a>
                            </li>
                            
                            <li class="binByte">
                                
                                <p class="objControlText">Controles</p>
                                
                                <form action="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/set-{{objectNumber}}" method="post">
                                    
                                    <!-- checkboxes / bits -->
                                    
                                    %for i in range(object.size):
                                        
                                        <div class="byteBox">
                                            
                                            <p class="byteNumber">Byte {{i}}</p>
                                        
                                        <div class="bitSet">
                                        
                                        %for j in range(8)[::-1]:
                                        
                                        <div class="bitBox">
                                            
                                            <p class="bitNumber">{{j}}</p>
                                            <input type="checkbox" id="bit-{{i}}-{{j}}" value="{{hex(1<<j)}}" class="bitCheck">
                                            
                                        </div>
                                        
                                        %end
                                        
                                        </div>
                                        
                                        </div>
                                    
                                    %end
                                    
                                    <button type="submit" class="objSetButton" name="save">
                                        Aplicar
                                    </button>
                                    
                                </form>
                                
                            </li>
                        
                        %end
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeUnsignedInt:
                    
                        %if object.objectDataTypeInfo in [hbusSlaveObjectDataType.dataTypeUintPercent,hbusSlaveObjectDataType.dataTypeUintLogPercent,hbusSlaveObjectDataType.dataTypeUintLinPercent]:
                        
                            <li class="percent">
                                <a onclick="loadObject({{objectNumber}})">
                                    <p>{{object.description}}</p>
                                    %if canRead:
                                    <span id="OVAL-{{objectNumber}}" class="hbusObjectValue">
                                        %if object.last_value == None:
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
                        
                            <li class="integer">
                                <a onclick="loadObject({{objectNumber}})">
                                    <p>{{object.description}}</p>
                                    %if canRead:
                                    <span id="OVAL-{{objectNumber}}" class="hbusObjectValue">
                                        %if object.last_value == None:
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
                    
                            <li class="integer">
                                <a onclick="loadObject({{objectNumber}})">
                                    <p>{{object.description}}</p>
                                    %if canRead:
                                    <span id="OVAL-{{objectNumber}}" class="hbusObjectValue">
                                        %if object.last_value == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    %end
                                </a>
                            </li>
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeFixedPoint:
                    
                            <li class="integer">
                                <a onclick="loadObject({{objectNumber}})">
                                    <p>{{object.description}}</p>
                                    %if canRead:
                                    <span id="OVAL-{{objectNumber}}" class="hbusObjectValue">
                                        %if object.last_value == None:
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
