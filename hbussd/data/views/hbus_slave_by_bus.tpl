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
                
            </div>
        </aside>
    </header>
	
    <section class="hbusDeviceDescription">
        <a class ="left">Active devices</a>
        <div class="right">
            %if busNumber != "255":
                BUS {{busNumber}}
            %else:
                All devices
            %end
        </div>
    </section>
    
</div>
	
	<div class="hbusMMain">
	       
	  <span class="center">
	      <span class="centerWrap">
	      
        	   <ul class="devGrid">
        	       
        	       %for slave in slaveList:
        	       
        	           %if slave.basicInformationRetrieved == False:
        	               %continue
        	           %end
        	       
        	           <li>
        	               <a href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}">
        	                   <div class="fill"> </div>
        	                   <p>{{slave.hbusSlaveDescription}}</p>
        	               </a>
        	           </li>
        
        	       %end
        	       
        	   </ul>
        </span>
      </span>
    </div>
    
</div>
        
</html>
