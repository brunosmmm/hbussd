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
                <div class = "statusText">Dispositivos <br /> ativos</div>
                
            </div>
            
            <div class="hbusStatus">
                
            </div>
        </aside>
    </header>
    
</div>
	
	<section class="hbusActiveDevices">
	   Dispositivos ativos
	</section>
	
	<div class="hbusMMain">
	       
	   <span class="center">
	       <span class="centerWrap">
        	   <ul class="busGrid">
        	       
        	       %for activeBus in masterStatus.activeBusses:
        	           <li>
        	               <a href="bus/{{activeBus}}">
        	                   <div class="fill"> </div>
        	                   <p>BUS {{activeBus}}</p>
        	               </a>
        	           </li>
        	       %end
        	       
        	           <li>
        	               <a href="bus/255">
        	                   <div class="fill"> </div>
        	                   <p>Todos</p>
        	               </a>
        	           </li>
        	       
        	   </ul>
            </span>
       </span>
	           
    </div>
    
</div>
        
</html>