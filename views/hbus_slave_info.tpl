<!DOCTYPE html>
<html>
	<head>
		<title>HBUS Server</title>
	</head>

	<div style="text-align:center">
		<h1>HBUS Server</h1>
	</div>
	
	%if slave != None:
		<h3>{{slave.hbusSlaveDescription}}</h3>
	%else:
		<h3>Erro! Dispositivo não encontrado!</h3>
	%end
	
	<table border="1">
		<tr>
			<th>ID</th>
			<th>Descrição</th>
			<th>Permissões</th>
			<th>Tamanho</th>
		</tr>
		%i = 1
		%for object in slave.hbusSlaveObjects.values():
			
			<tr>
				<td>{{i}}</td>
				<td>{{object.objectDescription}}</td>
				<td>
				%if object.objectPermissions == 1:
					R
				%elif object.objectPermissions == 2:
					W
				%else
					RW
				%end
				</td>
				<td>{{object.objectSize}}</td>
			</tr>
			
			%i += 1
			
		%end
	</table>

	


</html>