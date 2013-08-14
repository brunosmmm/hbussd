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
        <a class="left" href="/bus/{{busNumber}}">Dispositivos ativos</a>
        <div class="right">
            %if busNumber != "255":
                BUS {{busNumber}}
            %else:
                Todos
            %end
        </div>
    </section>
	
	<div class=hbusMMain>
	
	       
	   <ul class="devGrid">
	       
	       %for slave in slaveList:
	           <li><a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}">{{slave.hbusSlaveDescription}}</a></li>
	       %end
	       
	   </ul>
        
    </div>
    
</div>
        
</html>