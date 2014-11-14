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
        
        <link rel="stylesheet" href="/static/normalize.css">
        <script type="text/javascript" src="/static/jquery-2.0.3.min.js" ></script>
        <script type="text/javascript" src="/static/jquery.als-1.1.min.js" ></script>
        
        <script type="text/javascript">
            //ALS INIT
            $(document).ready(function(){
                
                var $w = $(window).width();
                var $h = $(window).height();
                
                if ($w>$h)
                {
                    $("#readObjectsList").als({
                        %if readObjCount < 5:
                            visible_items: {{readObjCount}},
                        %else:
                            visible_items: 5,
                        %end
                        orientation: "horizontal"
                    });
                    
                    $("#writeObjectsList").als({
                        %if writeObjCount < 5:
                            visible_items: {{writeObjCount}},
                        %else:
                            visible_items: 5,
                        %end
                        orientation: "horizontal"
                    }); 
                 }
                 else
                 {
                    $("#readObjectsList").als({
                        %if readObjCount < 3:
                            visible_items: {{readObjCount}},
                        %else:
                            visible_items: 3,
                        %end
                        orientation: "vertical"
                    }); 
                    
                    $("#writeObjectsList").als({
                        %if writeObjCount < 3:
                            visible_items: {{writeObjCount}},
                        %else:
                            visible_items: 3,
                        %end
                        orientation: "vertical"
                    }); 
                 }

            }); 
        </script>
        
        <script type="text/javascript">
            //ALS RECONFIGURE
            $(window).resize(function(){
                
                var $w = $(window).width();
                var $h = $(window).height();
                
                if ($w>$h)
                {
                    $("#readObjectsList").als({
                        %if readObjCount < 5:
                            visible_items: {{readObjCount}},
                        %else:
                            visible_items: 5,
                        %end
                        orientation: "horizontal"
                    });
                    
                     $("#writeObjectsList").als({
                        %if writeObjCount < 5:
                            visible_items: {{writeObjCount}},
                        %else:
                            visible_items: 5,
                        %end
                        orientation: "horizontal"
                    });
                 }
                 else
                 {
                    $("#readObjectsList").als({
                        %if readObjCount < 3:
                            visible_items: {{readObjCount}},
                        %else:
                            visible_items: 3,
                        %end
                        orientation: "vertical"
                    }); 
                    $("#writeObjectsList").als({
                        %if writeObjCount < 3:
                            visible_items: {{writeObjCount}},
                        %else:
                            visible_items: 3,
                        %end
                        orientation: "vertical"
                    }); 
                 }

            }); 
        </script>
        
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
                <div class = "statusText">Active <br /> devices</div>
                
            </div>
            
            <div class="hbusStatus">
                <div class="statusText"><a href="/bus/{{slave.hbusSlaveAddress.hbusAddressBusNumber}}">BUS {{slave.hbusSlaveAddress.hbusAddressBusNumber}}</a></div>
            </div>
        </aside>
    </header>
    
    <section class="hbusDeviceDescription">
        <a class="left">{{slave.hbusSlaveDescription}}</a>
        <div class="right">&lt;{{hex(slave.hbusSlaveUniqueDeviceInfo)}}&gt; @ {{slave.hbusSlaveAddress.hbusAddressBusNumber}}:{{slave.hbusSlaveAddress.hbusAddressDevNumber}}</div>
    </section>

</div>
    
    <div class="hbusMMain">
        
        %if readObjCount > 0:
        
        <div class="als-container readObjects" id="readObjectsList">
            
            <span class="als-prev"><img src="/static/prev.png" alt="prev" title="previous" /></span>
            
            <div class="als-viewport">
        
            <ul class="als-wrapper objGrid">
                
                %i = 0
                %for object in slave.hbusSlaveObjects.values():
                
                    %i += 1
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
                        
                            <li class="als-item boolsw">
                                <a onclick="loadObject({{i}})">
                                    <p>{{object.objectDescription}}</p>                               
                                    <span id="OVAL-{{i}}" class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                    
                                </a>
                            </li>
                            
                        %else:
                        
                            <li class="als-item byte">
                                <a onclick="loadObject({{i}})">
                                    <p>{{object.objectDescription}}</p>
                                    <span id="OVAL-{{i}}" class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                </a>
                            </li>
                        
                        %end
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeUnsignedInt:
                    
                        %if object.objectDataTypeInfo in [hbusSlaveObjectDataType.dataTypeUintPercent,hbusSlaveObjectDataType.dataTypeUintLogPercent,hbusSlaveObjectDataType.dataTypeUintLinPercent]:
                        
                            <li class="als-item percent">
                                <a onclick="loadObject({{i}})">
                                    <p>{{object.objectDescription}}</p>
                                    <span id="OVAL-{{i}}" class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                </a>
                            </li>
                        
                        %else:
                        
                            <li class="als-item integer">
                                <a onclick="loadObject({{i}})">
                                    <p>{{object.objectDescription}}</p>
                                    <span id="OVAL-{{i}}" class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                </a>
                            </li>
                        
                        %end
                        
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeInt:
                    
                            <li class="als-item integer">
                                <a onclick="loadObject({{i}})">
                                    <p>{{object.objectDescription}}</p>
                                    <span id="OVAL-{{i}}" class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                </a>
                            </li>
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeFixedPoint:
                    
                            <li class="als-item integer">
                                <a onclick="loadObject({{i}})">
                                    <p>{{object.objectDescription}}</p>
                                    <span id="OVAL-{{i}}" class="hbusObjectValue">
                                        %if object.objectLastValue == None:
                                            ?
                                        %else:
                                            {{object.getFormattedValue()}}
                                        %end
                                    </span>
                                </a>
                            </li>
                    
                    %end
                    
               %end
                
            </ul>
            
            </div>
            
            <span class="als-next"><img src="/static/next.png" alt="next" title="next" /></span> <!-- "next" button -->
        
        </div>
        
        %end
        
        %if writeObjCount > 0:
        
        <div class="als-container writeObjects" id="writeObjectsList">
            
            <span class="als-prev"><img src="/static/prev.png" alt="prev" title="previous" /></span>
            
            <div class="als-viewport">
        
            <ul class="als-wrapper objGrid">
                
                %i = 0
                %for object in slave.hbusSlaveObjects.values():
                    
                    %i += 1
                    
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
                        
                            <li class="als-item boolsw">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/set-{{i}}">
                                    <p>{{object.objectDescription}}</p>
                                </a>
                            </li>
                            
                        %else:
                        
                            <li class="als-item byte">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/set-{{i}}">
                                    <p>{{object.objectDescription}}</p>
                                </a>
                            </li>
                        
                        %end
                    
                    %elif object.objectDataType == hbusSlaveObjectDataType.dataTypeUnsignedInt:
                    
                        %if object.objectDataTypeInfo in [hbusSlaveObjectDataType.dataTypeUintPercent,hbusSlaveObjectDataType.dataTypeUintLogPercent,hbusSlaveObjectDataType.dataTypeUintLinPercent]:
                        
                            <li class="als-item percent">
                                <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}/set-{{i}}">
                                    <p>{{object.objectDescription}}</p>
                                </a>
                            </li>
                        
                        %else:
                        
                            %pass
                        
                        %end
                    
                    %end
                    
               %end
                
            </ul>
            
            </div>
            
             <span class="als-next"><img src="/static/next.png" alt="next" title="next" /></span> <!-- "next" button -->
        
        </div>
        
        %end
        
    </div>
    
</div>
        
</html>
