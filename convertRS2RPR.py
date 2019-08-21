
'''
Redshift to RadeonProRender Converter

History:
v.1.0 - first version
v.1.1 - IBL issue, Displacement convertopn in rsMatarial
v.1.2 - Link To Reflaction convertion change in rsMaterial
v.1.3 - Area light convertion
v.1.4 - Ambient Occlusion, Fresnel support
v.1.5 - Clean scene from redshift (dialog)
v.1.6 - Redshift Material Blender convertation, updated all material convertation
v.1.7 - Fix bugs, deleting lights with transforms.
v.1.8 - Opacity convertation in Redshift Material, rsColorLayer support.
v.1.9 - Fix area light conversion
v.2.0 - Add bumpBlend support
v.2.1 - Fix bug with channel converting, fix bug with creating extra materials.
v.2.2 - ColorCorrection support. Update physical light & subsurface material conversion.
v.2.3 - rsVolumeScattering conversion
v.2.4 - Added the ability to re-convert scene
v.2.5 - RedshiftArchitectural conversion updates.
v.2.6 - RedshiftIncandescent conversion updates.
v.2.7 - RedshiftMaterial & RedshiftSubSurface conversion updates
v.2.8 - RedshiftIESLight & RedshiftPortalLight conversion
v.2.9 - Fresnel mode & ss units mode conversion updates in RedshiftMaterial 
		Conversion of light units
		Update conversion of color+edge tint mode in RedshiftMaterial, VolumeScattering update
		Update conversion of metalness in RedshiftArchitectural
		Multiscatter layers conversion update in RedshiftMaterial
v.2.10 - Intensity conversion in dome light
		Intensity conversion in Redshift Environment
		Update conversion of fresnel modes in RedshiftMaterial
v.2.11 - Fix displacement conversion in Redshift Material
		Update image unit type conversion in physical light
v.2.12 - Update units type of physical light conversion
v.2.13 - Update opacity conversion, fix material & bump map conversion
		Update rsColorLayer conversion. Fix bug with file color space
		Global settings conversion
v.2.14 - Fixed issue with group of lights
		Fixed issue with unassign materials with shader catcher
		bump2d and multiplyDivide nodes support
		Improve conversion of global render settings
		Improve rsBumpMap and rsNormalMap conversion
		Improve metal conversion in rsArchitectural
		Improve opacity conversion in rsMaterial and rsIncandescent
		rsNoise node support
		rsSprite material support
		Improve rsMaterial Translucency conversion
v.2.15 - Improve normal map conversion in rsMaterial and rsArchitectural
		Improvements of translucency conversion in rsMaterial
		Fixed bug with unsupported nodes conversion
		Fixed bug with temperature in RPRPhysical lights
		Improve rsArchitectural conversion
v.2.16 - Improve rsArchitectural and rsMaterial conversion
		Changed BumpBlender conversion 
		Photoexposure conversion
v.2.17 - Multiscatter SSS improvements

'''

import maya.mel as mel
import maya.cmds as cmds
import time
import math
import traceback


# log functions

def write_converted_property_log(rpr_name, rs_name, rpr_attr, rs_attr):

	try:
		file_path = cmds.file(q=True, sceneName=True) + ".log"
		with open(file_path, 'a') as f:
			f.write(u"    property {}.{} is converted to {}.{}   \r\n".format(rs_name, rs_attr, rpr_name, rpr_attr).encode('utf-8'))
	except Exception as ex:
		pass


def write_own_property_log(text):

	try:
		file_path = cmds.file(q=True, sceneName=True) + ".log"
		with open(file_path, 'a') as f:
			f.write("    {}   \r\n".format(text))
	except Exception as ex:
		pass


def start_log(rs, rpr):

	try:
		text  = u"Found node: \r\n    name: {} \r\n".format(rs).encode('utf-8')
		text += "type: {} \r\n".format(cmds.objectType(rs))
		text += u"Converting to: \r\n    name: {} \r\n".format(rpr).encode('utf-8')
		text += "type: {} \r\n".format(cmds.objectType(rpr))
		text += "Conversion details: \r\n"

		file_path = cmds.file(q=True, sceneName=True) + ".log"
		with open(file_path, 'a') as f:
			f.write(text)
	except Exception as ex:
		pass
	


def end_log(rs):

	try:
		text  = u"Conversion of {} is finished.\n\n \r\n".format(rs).encode('utf-8')

		file_path = cmds.file(q=True, sceneName=True) + ".log"
		with open(file_path, 'a') as f:
			f.write(text)
	except Exception as ex:
		pass
		

# additional fucntions

def copyProperty(rpr_name, conv_name, rpr_attr, conv_attr):

	# full name of attribute
	conv_field = conv_name + "." + conv_attr
	rpr_field = rpr_name + "." + rpr_attr
	rs_type = type(getProperty(conv_name, conv_attr))
	rpr_type = type(getProperty(rpr_name, rpr_attr))

	try:
		listConnections = cmds.listConnections(conv_field)
		# connection convert
		if listConnections and cmds.objectType(listConnections[0]) != "transform":
			obj, channel = cmds.connectionInfo(conv_field, sourceFromDestination=True).split('.')
			source_name, source_attr = convertMaterial(obj, channel).split('.')
			connectProperty(source_name, source_attr, rpr_name, rpr_attr)
		# complex color conversion for each channel (RGB/XYZ/HSV)
		elif not listConnections and rs_type == tuple:
			# RGB (redshift)
			if cmds.objExists(conv_field + "R") and cmds.objExists(rpr_field + "R"):
				copyProperty(rpr_name, conv_name, rpr_attr + "R", conv_attr + "R")
				copyProperty(rpr_name, conv_name, rpr_attr + "G", conv_attr + "G")
				copyProperty(rpr_name, conv_name, rpr_attr + "B", conv_attr + "B")
			if cmds.objExists(conv_field + "R") and cmds.objExists(rpr_field + "X"):
				copyProperty(rpr_name, conv_name, rpr_attr + "X", conv_attr + "R")
				copyProperty(rpr_name, conv_name, rpr_attr + "Y", conv_attr + "G")
				copyProperty(rpr_name, conv_name, rpr_attr + "Z", conv_attr + "B")
			if cmds.objExists(conv_field + "R") and cmds.objExists(rpr_field + "H"):
				copyProperty(rpr_name, conv_name, rpr_attr + "H", conv_attr + "R")
				copyProperty(rpr_name, conv_name, rpr_attr + "S", conv_attr + "G")
				copyProperty(rpr_name, conv_name, rpr_attr + "V", conv_attr + "B")
			# XYZ (redshift)
			if cmds.objExists(conv_field + "X") and cmds.objExists(rpr_field + "R"):
				copyProperty(rpr_name, conv_name, rpr_attr + "R", conv_attr + "X")
				copyProperty(rpr_name, conv_name, rpr_attr + "G", conv_attr + "Y")
				copyProperty(rpr_name, conv_name, rpr_attr + "B", conv_attr + "Z")
			if cmds.objExists(conv_field + "X") and cmds.objExists(rpr_field + "X"):
				copyProperty(rpr_name, conv_name, rpr_attr + "X", conv_attr + "X")
				copyProperty(rpr_name, conv_name, rpr_attr + "Y", conv_attr + "Y")
				copyProperty(rpr_name, conv_name, rpr_attr + "Z", conv_attr + "Z")
			if cmds.objExists(conv_field + "X") and cmds.objExists(rpr_field + "H"):
				copyProperty(rpr_name, conv_name, rpr_attr + "H", conv_attr + "X")
				copyProperty(rpr_name, conv_name, rpr_attr + "S", conv_attr + "Y")
				copyProperty(rpr_name, conv_name, rpr_attr + "V", conv_attr + "Z")
			# HSV (redshift)
			if cmds.objExists(conv_field + "H") and cmds.objExists(rpr_field + "R"):
				copyProperty(rpr_name, conv_name, rpr_attr + "R", conv_attr + "H")
				copyProperty(rpr_name, conv_name, rpr_attr + "G", conv_attr + "S")
				copyProperty(rpr_name, conv_name, rpr_attr + "B", conv_attr + "V")
			if cmds.objExists(conv_field + "H") and cmds.objExists(rpr_field + "X"):
				copyProperty(rpr_name, conv_name, rpr_attr + "X", conv_attr + "H")
				copyProperty(rpr_name, conv_name, rpr_attr + "Y", conv_attr + "S")
				copyProperty(rpr_name, conv_name, rpr_attr + "Z", conv_attr + "V")
			if cmds.objExists(conv_field + "H") and cmds.objExists(rpr_field + "H"):
				copyProperty(rpr_name, conv_name, rpr_attr + "H", conv_attr + "H")
				copyProperty(rpr_name, conv_name, rpr_attr + "S", conv_attr + "S")
				copyProperty(rpr_name, conv_name, rpr_attr + "V", conv_attr + "V")

		# field conversion
		else:
			if rs_type == rpr_type:
				setProperty(rpr_name, rpr_attr, getProperty(conv_name, conv_attr))
			elif rs_type == tuple and rpr_type == float:
				if cmds.objExists(conv_field + "R"):
					conv_attr += "R"
				elif cmds.objExists(conv_field + "X"):
					conv_attr += "X"
				elif cmds.objExists(conv_field + "H"):
					conv_attr += "H"
				setProperty(rpr_name, rpr_attr, getProperty(conv_name, conv_attr))
			elif rs_type == float and rpr_type == tuple:
				if cmds.objExists(rpr_field + "R"):
					rpr_attr1 = rpr_attr + "R"
					rpr_attr2 = rpr_attr + "G"
					rpr_attr3 = rpr_attr + "B"
				elif cmds.objExists(rpr_field + "X"):
					rpr_attr1 = rpr_attr + "X"
					rpr_attr2 = rpr_attr + "Y"
					rpr_attr3 = rpr_attr + "Z"
				elif cmds.objExists(conv_field + "H"):
					rpr_attr1 = rpr_attr + "H"
					rpr_attr2 = rpr_attr + "S"
					rpr_attr3 = rpr_attr + "V"
				setProperty(rpr_name, rpr_attr1, getProperty(conv_name, conv_attr))
				setProperty(rpr_name, rpr_attr2, getProperty(conv_name, conv_attr))
				setProperty(rpr_name, rpr_attr3, getProperty(conv_name, conv_attr))

			write_converted_property_log(rpr_name, conv_name, rpr_attr, conv_attr)
	except Exception as ex:
		traceback.print_exc()
		print(u"Error while copying from {} to {}".format(conv_field, rpr_field).encode('utf-8'))


def setProperty(rpr_name, rpr_attr, value):

	# full name of attribute
	rpr_field = rpr_name + "." + rpr_attr

	try:
		if type(value) == tuple:
			cmds.setAttr(rpr_field, value[0], value[1], value[2])
		elif type(value) == str or type(value) == unicode:
			cmds.setAttr(rpr_field, value, type="string")
		else:
			cmds.setAttr(rpr_field, value)
		write_own_property_log(u"Set value {} to {}.".format(value, rpr_field).encode('utf-8'))
	except Exception as ex:
		traceback.print_exc()
		print(u"Set value {} to {} is failed. Check the values and their boundaries. ".format(value, rpr_field).encode('utf-8'))
		write_own_property_log(u"Set value {} to {} is failed. Check the values and their boundaries. ".format(value, rpr_field).encode('utf-8'))


def getProperty(material, attr):

	# full name of attribute
	field = material + "." + attr
	try:
		value = cmds.getAttr(field)
		if type(value) == list:
			value = value[0]
	except Exception as ex:
		traceback.print_exc()
		write_own_property_log(u"There is no {} field in this node. Check the field and try again. ".format(field).encode('utf-8'))
		return

	return value

def mapDoesNotExist(rs_name, rs_attr):

	# full name of attribute
	rs_field = rs_name + "." + rs_attr

	try:
		listConnections = cmds.listConnections(rs_field)
		if listConnections:
			return 0
	except Exception as ex:
		traceback.print_exc()
		write_own_property_log(u"There is no {} field in this node. Check the field and try again. ".format(rs_field).encode('utf-8'))
		return

	return 1


def connectProperty(source_name, source_attr, rpr_name, rpr_attr):

	# full name of attribute
	source = source_name + "." + source_attr
	rpr_field = rpr_name + "." + rpr_attr

	try:
		source_type = type(getProperty(source_name, source_attr))
		dest_type = type(getProperty(rpr_name, rpr_attr))

		if rpr_attr in ("surfaceShader", "volumeShader"):
			cmds.connectAttr(source, rpr_field, force=True)

		elif cmds.objExists(source_name + ".outAlpha") and cmds.objExists(source_name + ".outColor"):
			if cmds.objectType(source_name) == "file":
				setProperty(source_name, "ignoreColorSpaceFileRules", 1)

			if source_type == dest_type:
				cmds.connectAttr(source, rpr_field, force=True)
			elif source_type == tuple and dest_type == float:
				source = source_name + ".outAlpha"
				cmds.connectAttr(source, rpr_field, force=True)
			elif source_type == float and dest_type == tuple:
				source = source_name + ".outColor"
				cmds.connectAttr(source, rpr_field, force=True)

		else:
			if source_type == dest_type:
				cmds.connectAttr(source, rpr_field, force=True)
			elif source_type == tuple and dest_type == float:
				if cmds.objExists(source + "R"):
					source += "R"
				elif cmds.objExists(source + "X"):
					source += "X"
				elif cmds.objExists(source + "X"):
					source += "H"
				cmds.connectAttr(source, rpr_field, force=True)
			elif source_type == float and dest_type == tuple:
				if cmds.objExists(rpr_field + "R"):
					rpr_field1 = rpr_field + "R"
					rpr_field2 = rpr_field + "G"
					rpr_field3 = rpr_field + "B"
				elif cmds.objExists(rpr_field + "X"):
					rpr_field1 = rpr_field + "X"
					rpr_field2 = rpr_field + "Y"
					rpr_field3 = rpr_field + "Z"
				elif cmds.objExists(rpr_field + "H"):
					rpr_field1 = rpr_field + "H"
					rpr_field2 = rpr_field + "S"
					rpr_field3 = rpr_field + "V"
				cmds.connectAttr(source, rpr_field1, force=True)
				cmds.connectAttr(source, rpr_field2, force=True)
				cmds.connectAttr(source, rpr_field3, force=True)

		write_own_property_log(u"Created connection from {} to {}.".format(source, rpr_field).encode('utf-8'))
	except Exception as ex:
		traceback.print_exc()
		print(u"Connection {} to {} is failed.".format(source, rpr_field).encode('utf-8'))
		write_own_property_log(u"Connection {} to {} is failed.".format(source, rpr_field).encode('utf-8'))


# displacement conversion
def convertDisplacement(displacement, displacement_file, rs_material, rpr_material):

	# get all shapes
	cmds.hyperShade(objects=rs_material)
	shapes = cmds.ls(sl=True)

	if len(shapes) > 1:
		for shape in shapes:
			rsEnableSubdivision = getProperty(shape, "rsEnableSubdivision")
			rsEnableDisplacement = getProperty(shape, "rsEnableDisplacement")
			featureDisplacement = getProperty(shape, "featureDisplacement")
			if (rsEnableSubdivision and rsEnableDisplacement) or featureDisplacement: 
				rprMaterial = convertMaterial(rs_material, "displacement_copy")
				rpr_sg = cmds.listConnections(rprMaterial, type="shadingEngine")[0]

				cmds.select(cl=True)
				cmds.select(shape, r=True)
				cmds.sets(forceElement=rpr_sg)

				setProperty(rprMaterial, "displacementEnable", 1)
				connectProperty(displacement_file, "outColor", rprMaterial, "displacementMap")

				if featureDisplacement:
					copyProperty(rprMaterial, shape, "displacementSubdiv", "renderSmoothLevel")
				else:
					rsMaxTessellationSubdivs = getProperty(shape, "rsMaxTessellationSubdivs")
					if rsMaxTessellationSubdivs > 7:
						rsMaxTessellationSubdivs = 7
					setProperty(rprMaterial, "displacementSubdiv", rsMaxTessellationSubdivs)

					osdVertBoundary = getProperty(shape, "osdVertBoundary")
					displacementBoundary = remap_value(osdVertBoundary, 2, 1, 1, 0)
					setProperty(rprMaterial, "displacementBoundary", displacementBoundary)

					displacementMax = getProperty(shape, "rsDisplacementScale") * getProperty(displacement, "scale")
					setProperty(rprMaterial, "displacementMax", displacementMax)

	else:
		setProperty(rpr_material, "displacementEnable", 1)
		connectProperty(displacement_file, "outColor", rpr_material, "displacementMap")
		copyProperty(rpr_material, displacement, "displacementMax", "scale")

		rsEnableSubdivision = getProperty(shapes[0], "rsEnableSubdivision")
		rsEnableDisplacement = getProperty(shapes[0], "rsEnableDisplacement")
		if rsEnableSubdivision and rsEnableDisplacement: 
			copyProperty(rpr_material, shapes[0], "displacementSubdiv", "rsMaxTessellationSubdivs")


def convertbump2d(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		bump_type = getProperty(rs, "bumpInterp")
		if not bump_type:
			rpr = cmds.shadingNode("RPRBump", asUtility=True)
			rpr = cmds.rename(rpr, rs + "_rpr")
		else:
			rpr = cmds.shadingNode("RPRNormal", asUtility=True)
			rpr = cmds.rename(rpr, rs + "_rpr")

		# Logging to file
		start_log(rs, rpr)

		# Fields conversion
		bumpConnections = cmds.listConnections(rs + ".bumpValue", type="file")
		if bumpConnections:
			connectProperty(bumpConnections[0], "outColor", rpr, "color")

		copyProperty(rpr, rs, "strength", "bumpDepth")

		# Logging to file
		end_log(rs)

	conversion_map = {
		"outNormal": "out",
		"outNormalX": "outX",
		"outNormalY": "outY",
		"outNormalZ": "outZ"
	}

	rpr += "." + conversion_map[source]
	return rpr


def convertmultiplyDivide(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		rpr = cmds.shadingNode("RPRArithmetic", asUtility=True)
		rpr = cmds.rename(rpr, rs + "_rpr")

		# Logging to file
		start_log(rs, rpr)

		# Fields conversion
		operation = getProperty(rs, "operation")
		operation_map = {
			1: 2,
			2: 3,
			3: 15
		}
		setProperty(rpr, "operation", operation_map[operation])
		copyProperty(rpr, rs, "inputA", "input1")
		copyProperty(rpr, rs, "inputB", "input2")
		
		# Logging to file
		end_log(rs)

	conversion_map = {
		"output": "out",
		"outputX": "outX",
		"outputY": "outY",
		"outputZ": "outZ"
	}

	rpr += "." + conversion_map[source]
	return rpr


def convertRedshiftNoise(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		noiseType = getProperty(rs, "noise_type")
		
		if noiseType == 0:
			rpr = cmds.shadingNode("simplexNoise", asUtility=True)
		elif noiseType == 2:
			rpr = cmds.shadingNode("fractal", asUtility=True)
		elif noiseType == 3:
			rpr = cmds.shadingNode("noise", asUtility=True)

		rpr = cmds.rename(rpr, rs + "_rpr")

		texture = cmds.shadingNode("place2dTexture", asUtility=True)

		connectProperty(texture, "outUV", rpr, "uv")
		connectProperty(texture, "outUvFilterSize", rpr, "uvFilterSize")
		setProperty(texture, "repeatU", getProperty(rs, "coord_scale_global") * getProperty(rs, "coord_scale0"))
		setProperty(texture, "repeatV", getProperty(rs, "coord_scale_global") * getProperty(rs, "coord_scale1"))
		copyProperty(texture, rs, "offsetU", "coord_offset0")
		copyProperty(texture, rs, "offsetV", "coord_offset1")

		# Logging to file (start)
		start_log(rs, rpr)

		setProperty(rpr, "amplitude", getProperty(rs, "noise_gain") / 2)

		if noiseType == 0:
			setProperty(rpr, "noiseType", 1)
			copyProperty(rpr, rs, "octaves", "noise_complexity")
			copyProperty(rpr, rs, "frequency", "noise_scale")
			copyProperty(rpr, rs, "distortionU", "distort")
			copyProperty(rpr, rs, "distortionV", "distort")
			copyProperty(rpr, rs, "distortionRatio", "distort_scale")
		elif noiseType == 2:
			copyProperty(rpr, rs, "frequencyRatio", "noise_scale")
		elif noiseType == 3:
			copyProperty(rpr, rs, "depthMax", "noise_complexity")
			copyProperty(rpr, rs, "frequencyRatio", "noise_scale")

		# Logging to file (end)
		end_log(rs)

	rpr += "." + source
	return rpr


# re-convert is not fully supported for this node (only scale field)
def convertRedshiftNormalMap(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		rpr = cmds.shadingNode("RPRNormal", asUtility=True)
		rpr = cmds.rename(rpr, rs + "_rpr")
		file = cmds.shadingNode("file", asTexture=True, isColorManaged=True)
		texture = cmds.shadingNode("place2dTexture", asUtility=True)

		connectProperty(texture, "coverage", file, "coverage")
		connectProperty(texture, "translateFrame", file, "translateFrame")
		connectProperty(texture, "rotateFrame", file, "rotateFrame")
		connectProperty(texture, "mirrorU", file, "mirrorU")
		connectProperty(texture, "mirrorV", file, "mirrorV")
		connectProperty(texture, "stagger", file, "stagger")
		connectProperty(texture, "wrapU", file, "wrapU")
		connectProperty(texture, "wrapV", file, "wrapV")
		connectProperty(texture, "repeatUV", file, "repeatUV")
		connectProperty(texture, "offset", file, "offset")
		connectProperty(texture, "rotateUV", file, "rotateUV")
		connectProperty(texture, "noiseUV", file, "noiseUV")
		connectProperty(texture, "vertexUvOne", file, "vertexUvOne")
		connectProperty(texture, "vertexUvTwo", file, "vertexUvTwo")
		connectProperty(texture, "vertexUvThree", file, "vertexUvThree")
		connectProperty(texture, "vertexCameraOne", file, "vertexCameraOne")
		connectProperty(texture, "outUV", file, "uv")
		connectProperty(texture, "outUvFilterSize", file, "uvFilterSize")
		copyProperty(texture, rs, "repeatU", "repeats0")
		copyProperty(texture, rs, "repeatV", "repeats1")

		if getProperty(rs, "flipY"):
			arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic, "inputA", (1, 1, 1))
			setProperty(arithmetic, "operation", 1)
			connectProperty(file, "outColorG", arithmetic, "inputBY")
			connectProperty(arithmetic, "outY", rpr, "colorG")
			connectProperty(file, "outColorR", rpr, "colorR")
			connectProperty(file, "outColorB", rpr, "colorB")
		else:
			connectProperty(file, "outColor", rpr, "color")

		setProperty(file, "colorSpace", "Raw")
		setProperty(file, "fileTextureName", getProperty(rs, "tex0"))
			
		# Logging to file (start)
		start_log(rs, rpr)

		copyProperty(rpr, rs, "strength", "scale")

		# Logging to file (end)
		end_log(rs)

	conversion_map = {
		"outDisplacementVector": "out",
		"outDisplacementVectorR": "outR",
		"outDisplacementVectorG": "outG",
		"outDisplacementVectorB": "outB"
	}

	rpr += "." + conversion_map[source]
	return rpr


def convertRedshiftAmbientOcclusion(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		rpr = cmds.shadingNode("RPRAmbientOcclusion", asUtility=True)
		rpr = cmds.rename(rpr, rs + "_rpr")

		# Logging to file
		start_log(rs, rpr)

		# Fields conversion
		copyProperty(rpr, rs, "unoccludedColor", "bright")
		copyProperty(rpr, rs, "occludedColor", "dark")
		copyProperty(rpr, rs, "radius", "spread")

		# Logging to file
		end_log(rs)

	conversion_map = {
		"outColor": "output",
		"outColorR": "outputR",
		"outColorG": "outputG",
		"outColorB": "outputB"
	}

	rpr += "." + conversion_map[source]
	return rpr


# re-convert for ior in unsupported
def convertRedshiftFresnel(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		rpr = cmds.shadingNode("RPRBlendValue", asUtility=True)
		
		fresnel = cmds.shadingNode("RPRFresnel", asUtility=True)
		fresnel = cmds.rename(fresnel, rs + "_rpr")

		connectProperty(fresnel, "out", rpr, "weight")
		copyProperty(fresnel, rs, "ior", "ior")

		# Logging to file
		start_log(rs, rpr)

		# Fields conversion
		copyProperty(rpr, rs, "inputA", "facing_color")
		copyProperty(rpr, rs, "inputB", "perp_color")

		# Logging to file
		end_log(rs)

	conversion_map = {
		"outColor": "out",
		"outColorR": "outR",
		"outColorG": "outG",
		"outColorB": "outB"
	}

	rpr += "." + conversion_map[source]
	return rpr

# deleted
def convertRedshiftColorCorrection(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		rpr = cmds.shadingNode("colorCorrect", asUtility=True)
		rpr = cmds.rename(rpr, rs + "_rpr")

		# Logging to file
		start_log(rs, rpr)

		# Fields conversion
		copyProperty(rpr, rs, "inColor", "input")
		copyProperty(rpr, rs, "hueShift", "hue")
		copyProperty(rpr, rs, "satGain", "saturation")
		copyProperty(rpr, rs, "valGain", "level")
		copyProperty(rpr, rs, "colGamma", "gamma")

		# Logging to file
		end_log(rs)

	rpr += "." + source
	return rpr


def convertRedshiftBumpMap(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		inputType = getProperty(rs, "inputType")
		if inputType == 0:
			rpr = cmds.shadingNode("RPRBump", asUtility=True)
		elif inputType == 1:
			rpr = cmds.shadingNode("RPRNormal", asUtility=True)
		elif inputType == 2:
			rpr = cmds.shadingNode("RPRNormal", asUtility=True)
			print(u"Bump map conversion ({}) is incorrect. You need conversion into Tangent Space.".format(rs).encode('utf-8'))

		rpr = cmds.rename(rpr, rs + "_rpr")

		# Logging to file
		start_log(rs, rpr)

		# Fields conversion
		copyProperty(rpr, rs, "strength", "scale")
		copyProperty(rpr, rs, "color", "input")

		# Logging to file
		end_log(rs)

	rpr += "." + source
	return rpr


def convertRedshiftColorLayer(rs, source):

	if cmds.objExists(rs + "_rpr"):
		rpr = rs + "_rpr"
	else:
		layer1_blend_mode = getProperty(rs, "layer1_blend_mode")
		if layer1_blend_mode in (2, 3, 4, 15):
			rpr = cmds.shadingNode("RPRArithmetic", asUtility=True)
			rpr = cmds.rename(rpr, rs + "_rpr")
		else:
			rpr = cmds.shadingNode("RPRBlendMaterial", asShader=True)
			rpr = cmds.rename(rpr, rs + "_rpr")

		# Logging to file
		start_log(rs, rpr)

		# Fields conversion
		if cmds.objectType(rpr) == "RPRArithmetic":
			conversion_map_operation = {
				2: 0,
				3: 1,
				4: 2,
				15: 3
			}
			setProperty(rpr, "operation", conversion_map_operation[layer1_blend_mode])
			copyProperty(rpr, rs, "inputA", "base_color")
			copyProperty(rpr, rs, "inputB", "layer1_color")
		else:
			copyProperty(rpr, rs, "color0", "base_color")
			copyProperty(rpr, rs, "color1", "layer1_color")
			copyProperty(rpr, rs, "weight", "layer1_mask")

		# Logging to file
		end_log(rs)

	if cmds.objectType(rpr) == "RPRArithmetic":
		conversion_map = {
			"outColor": "out",
			"outColorR": "outR",
			"outColorG": "outG",
			"outColorB": "outB"
		}
		source = conversion_map[source]

	rpr += "." + source
	return rpr


def convertRedshiftBumpBlender(rs, source):

	# duct tape
	if source != "bump_input":
		return

	rsMaterial = cmds.listConnections(rs + ".outColor")[0]
	
	blend_material = cmds.shadingNode("RPRBlendMaterial", asShader=True)
	
	rs_map = cmds.listConnections(rs + ".baseInput")
	if rs_map:
		if cmds.objectType(rs_map[0]) in ("RedshiftBumpMap", "RedshiftNormalMap"):
			rprMaterial = convertMaterial(rsMaterial, "bump_blender")
			connectProperty(rprMaterial, "outColor", blend_material, "color0")
			copyProperty(rprMaterial, rs, "normalMap", "baseInput")
			setProperty(rprMaterial, "normalMapEnable", 1)
			setProperty(rprMaterial, "useShaderNormal", 1)
			setProperty(rprMaterial, "reflectUseShaderNormal", 1)
			setProperty(rprMaterial, "refractUseShaderNormal", 1)
			setProperty(rprMaterial, "coatUseShaderNormal", 1)

	rs_map = cmds.listConnections(rs + ".bumpInput0")
	if rs_map:
		if cmds.objectType(rs_map[0]) in ("RedshiftBumpMap", "RedshiftNormalMap"):
			rprMaterial = convertMaterial(rsMaterial, "bump_blender")
			connectProperty(rprMaterial, "outColor", blend_material, "color1")
			copyProperty(blend_material, rs, "weight", "bumpWeight0")
			copyProperty(rprMaterial, rs, "normalMap", "bumpInput0")
			setProperty(rprMaterial, "normalMapEnable", 1)
			setProperty(rprMaterial, "useShaderNormal", 1)
			setProperty(rprMaterial, "reflectUseShaderNormal", 1)
			setProperty(rprMaterial, "refractUseShaderNormal", 1)
			setProperty(rprMaterial, "coatUseShaderNormal", 1)

	rs_map = cmds.listConnections(rs + ".bumpInput1")
	if rs_map:
		if cmds.objectType(rs_map[0]) in ("RedshiftBumpMap", "RedshiftNormalMap"):
			new_blend_material = cmds.shadingNode("RPRBlendMaterial", asShader=True)
			connectProperty(blend_material, "outColor", new_blend_material, "color0")
			rprMaterial = convertMaterial(rsMaterial, "bump_blender")
			connectProperty(rprMaterial, "outColor", new_blend_material, "color1")
			copyProperty(new_blend_material, rs, "weight", "bumpWeight1")
			copyProperty(rprMaterial, rs, "normalMap", "bumpInput1")
			setProperty(rprMaterial, "normalMapEnable", 1)
			setProperty(rprMaterial, "useShaderNormal", 1)
			setProperty(rprMaterial, "reflectUseShaderNormal", 1)
			setProperty(rprMaterial, "refractUseShaderNormal", 1)
			setProperty(rprMaterial, "coatUseShaderNormal", 1)
			blend_material = new_blend_material

	rs_map = cmds.listConnections(rs + ".bumpInput2")
	if rs_map:
		if cmds.objectType(rs_map[0]) in ("RedshiftBumpMap", "RedshiftNormalMap"):
			new_blend_material = cmds.shadingNode("RPRBlendMaterial", asShader=True)
			connectProperty(blend_material, "outColor", new_blend_material, "color0")
			rprMaterial = convertMaterial(rsMaterial, "bump_blender")
			connectProperty(rprMaterial, "outColor", new_blend_material, "color1")
			copyProperty(new_blend_material, rs, "weight", "bumpWeight2")
			copyProperty(rprMaterial, rs, "normalMap", "bumpInput2")
			setProperty(rprMaterial, "normalMapEnable", 1)
			setProperty(rprMaterial, "useShaderNormal", 1)
			setProperty(rprMaterial, "reflectUseShaderNormal", 1)
			setProperty(rprMaterial, "refractUseShaderNormal", 1)
			setProperty(rprMaterial, "coatUseShaderNormal", 1)
			blend_material = new_blend_material

	sg = blend_material + "SG"
	cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
	connectProperty(blend_material, "outColor", sg, "surfaceShader")

	cmds.hyperShade(objects=rsMaterial)
	cmds.sets(e=True, forceElement=sg)


# standart utilities
def convertStandartNode(rsMaterial, source):

	not_converted_list = ("materialInfo", "defaultShaderList", "shadingEngine", "place2dTexture")
	try:
		for attr in cmds.listAttr(rsMaterial):
			connection = cmds.listConnections(rsMaterial + "." + attr)
			if connection:
				if cmds.objectType(connection[0]) not in not_converted_list and attr not in (source, "message"):
					obj, channel = cmds.connectionInfo(rsMaterial + "." + attr, sourceFromDestination=True).split('.')
					source_name, source_attr = convertMaterial(obj, channel).split('.')
					connectProperty(source_name, source_attr, rsMaterial, attr)
	except Exception as ex:
		pass

	return rsMaterial + "." + source


# unsupported utilities
def convertUnsupportedNode(rsMaterial, source):

	if cmds.objExists(rsMaterial + "_UNSUPPORTED_NODE"):
		rpr = rsMaterial + "_UNSUPPORTED_NODE"
	else:
		rpr = cmds.shadingNode("RPRArithmetic", asUtility=True)
		rpr = cmds.rename(rpr, rsMaterial + "_UNSUPPORTED_NODE")

		# Logging to file
		start_log(rsMaterial, rpr)

		# 2 connection save
		try:
			setProperty(rpr, "operation", 0)
			unsupported_connections = 0
			for attr in cmds.listAttr(rsMaterial):
				connection = cmds.listConnections(rsMaterial + "." + attr)
				if connection:
					if cmds.objectType(connection[0]) not in ("materialInfo", "defaultShaderList", "shadingEngine") and attr not in (source, "message"):
						if unsupported_connections < 2:
							obj, channel = cmds.connectionInfo(rsMaterial + "." + attr, sourceFromDestination=True).split('.')
							source_name, source_attr = convertMaterial(obj, channel).split('.')
							valueType = type(getProperty(rsMaterial, attr))
							if valueType == tuple:
								if unsupported_connections < 1:
									connectProperty(source_name, source_attr, rpr, "inputA")
								else:
									connectProperty(source_name, source_attr, rpr, "inputB")
							else:
								if unsupported_connections < 1:
									connectProperty(source_name, source_attr, rpr, "inputAX")
								else:
									connectProperty(source_name, source_attr, rpr, "inputBX")
							unsupported_connections += 1
		except Exception as ex:
			traceback.print_exc()

		# Logging to file
		end_log(rsMaterial)

	sourceType = type(getProperty(rsMaterial, source))
	if sourceType == tuple:
		rpr += ".out"
	else:
		rpr += ".outX"

	return rpr


# Create default uber material for unsupported material
def convertUnsupportedMaterial(rsMaterial, source):

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRUberMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_UNSUPPORTED_MATERIAL"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")

		# Logging to file
		start_log(rsMaterial, rprMaterial)

		# set green color
		setProperty(rprMaterial, "diffuseColor", (0, 1, 0))

		end_log(rsMaterial)

	if source:
		rprMaterial += "." + source
	return rprMaterial


######################## 
## RedshiftArchitectural 
########################

def convertRedshiftArchitectural(rsMaterial, source):

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRUberMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")
			
		# Enable properties, which are default in RedShift
		defaultEnable(rprMaterial, rsMaterial, "diffuse", "diffuse_weight")
		defaultEnable(rprMaterial, rsMaterial, "reflections", "reflectivity")
		defaultEnable(rprMaterial, rsMaterial, "refraction", "transparency")
		defaultEnable(rprMaterial, rsMaterial, "emissive", "incandescent_scale")
		defaultEnable(rprMaterial, rsMaterial, "clearCoat", "refl_base")

		# Logging to file
		start_log(rsMaterial, rprMaterial)

		# diffuse
		copyProperty(rprMaterial, rsMaterial, "diffuseColor", "diffuse") 
		copyProperty(rprMaterial, rsMaterial, "diffuseWeight", "diffuse_weight")
		copyProperty(rprMaterial, rsMaterial, "diffuseRoughness", "diffuse_roughness")
		
		# primary reflection (reflection)
		
		if not mapDoesNotExist(rsMaterial, "refl_color"):
			connection = cmds.listConnections(rsMaterial + ".refl_color", type="file")
			if connection:
				setProperty(connection[0], "colorSpace", "Raw")
		copyProperty(rprMaterial, rsMaterial, "reflectColor", "refl_color")
		copyProperty(rprMaterial, rsMaterial, "reflectWeight", "reflectivity")

		if getProperty(rsMaterial, "brdf_fresnel"):
			ior = getProperty(rsMaterial, "brdf_fresnel_ior")
			if ior > 10:
				setProperty(rprMaterial, "reflectIOR", 10)
			else:
				setProperty(rprMaterial, "reflectIOR", ior)
		else:
			refl = getProperty(rsMaterial, "brdf_0_degree_refl")
			ior = -1 * (refl + 1 + 2 * math.sqrt(refl) / (refl - 1))
			if ior > 10:
				setProperty(rprMaterial, "reflectIOR", 10)
			else:
				setProperty(rprMaterial, "reflectIOR", ior)

		if mapDoesNotExist(rsMaterial, "refl_gloss"):  
			gloss = 1 - getProperty(rsMaterial, "refl_gloss")
			setProperty(rprMaterial, "reflectRoughness", gloss)
		else:
			if cmds.objectType(cmds.listConnections(rsMaterial + ".refl_gloss")[0]) == "reverse":
				copyProperty(rprMaterial, rsMaterial, "reflectRoughness", "refl_gloss")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputBX", "refl_gloss")
				connectProperty(arithmetic, "outX", rprMaterial, "reflectRoughness")

		setProperty(rprMaterial, "reflectAnisotropy", getProperty(rsMaterial, "anisotropy") * 2)
		copyProperty(rprMaterial, rsMaterial, "reflectAnisotropyRotation", "anisotropy_rotation")

		setProperty(rprMaterial, "reflectMetalMaterial", getProperty(rsMaterial, "refl_is_metal"))

		brdf_fresnel_type = getProperty(rsMaterial, "brdf_fresnel_type")
		if brdf_fresnel_type: # conductor
			brdf_extinction_coeff = getProperty(rsMaterial, "brdf_extinction_coeff")
			if brdf_extinction_coeff > 2:
				setProperty(rprMaterial, "reflectMetalMaterial", 1)
				setProperty(rprMaterial, "reflectMetalness", 1)

				if mapDoesNotExist(rsMaterial, "diffuse_weight"):
					setProperty(rprMaterial, "diffuseWeight", 0)
				if mapDoesNotExist(rsMaterial, "reflectivity"):
					setProperty(rprMaterial, "reflectWeight", 1)

				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				copyProperty(arithmetic, rsMaterial, "inputA", "diffuse")
				if not mapDoesNotExist(rsMaterial, "refl_color"):
					connection = cmds.listConnections(rsMaterial + ".refl_color", type="file")
					if connection:
						setProperty(connection[0], "colorSpace", "Raw")
				copyProperty(arithmetic, rsMaterial, "inputB", "refl_color")
				setProperty(arithmetic, "operation", 20)
				connectProperty(arithmetic, "out", rprMaterial, "reflectColor")

		# sec reflection (Coat)
		copyProperty(rprMaterial, rsMaterial, "coatWeight", "refl_base") 
		copyProperty(rprMaterial, rsMaterial, "coatColor", "refl_base_color")

		if mapDoesNotExist(rsMaterial, "refl_base_gloss"):  
			gloss = 1 - getProperty(rsMaterial, "refl_base_gloss")
			setProperty(rprMaterial, "coatRoughness", gloss)
		else:
			if cmds.objectType(cmds.listConnections(rsMaterial, "refl_base_gloss")[0]) == "reverse":
				copyProperty(rprMaterial, rsMaterial, "refl_base_gloss", "coatRoughness")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputBX", "refl_base_gloss")
				connectProperty(arithmetic, "outX", rprMaterial, "coatRoughness")

		if getProperty(rsMaterial, "brdf_base_fresnel"):
			if getProperty(rsMaterial, "brdf_base_fresnel_type"):
				coat_ior = getProperty(rsMaterial, "brdf_base_fresnel_ior") + getProperty(rsMaterial, "brdf_base_extinction_coeff")
			else:
				coat_ior = getProperty(rsMaterial, "brdf_base_fresnel_ior")

			if coat_ior > 10:
				setProperty(rprMaterial, "coatIor", 10)
			else:
				setProperty(rprMaterial, "coatIor", coat_ior)
		else:
			refl = getProperty(rsMaterial, "brdf_base_0_degree_refl")
			ior = -1 * (refl + 1 + 2 * math.sqrt(refl) / (refl - 1))
			if ior > 10:
				setProperty(rprMaterial, "coatIor", 10)
			else:
				setProperty(rprMaterial, "coatIor", ior)
			
		# refraction
		copyProperty(rprMaterial, rsMaterial, "refractColor", "refr_color")
		copyProperty(rprMaterial, rsMaterial, "refractWeight", "transparency")
		copyProperty(rprMaterial, rsMaterial, "refractThinSurface", "thin_walled")
		copyProperty(rprMaterial, rsMaterial, "refractIor", "refr_ior")

		if mapDoesNotExist(rsMaterial, "refr_gloss"):   
			gloss = 1 - getProperty(rsMaterial, "refr_gloss")
			setProperty(rprMaterial, "refractRoughness", gloss)
		else:
			if cmds.objectType(cmds.listConnections(rsMaterial, "refr_gloss")[0]) == "reverse":
				copyProperty(rprMaterial, rsMaterial, "refr_gloss", "refractRoughness")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputBX", "refr_gloss")
				connectProperty(arithmetic, "outX", rprMaterial, "refractRoughness")
				
		fog_enable = getProperty(rsMaterial, "refr_falloff_on")
		if fog_enable:
			copyProperty(rprMaterial, rsMaterial, "refractAbsorptionDistance", "refr_falloff_dist")
		
		end_color_enable = getProperty(rsMaterial, "refr_falloff_color_on")
		if end_color_enable:
			copyProperty(rprMaterial, rsMaterial, "refractAbsorbColor", "refr_falloff_color") 
		else: 
			copyProperty(rprMaterial, rsMaterial, "refractAbsorbColor", "refr_color")
		
		setProperty(rprMaterial, "refractAllowCaustics", getProperty(rsMaterial, "do_refractive_caustics"))
			
		# emissive
		copyProperty(rprMaterial, rsMaterial, "emissiveColor", "additional_color")
		copyProperty(rprMaterial, rsMaterial, "emissiveWeight", "incandescent_scale")

		if getProperty(rsMaterial, "refr_translucency"):
			setProperty(rprMaterial, "separateBackscatterColor", 1)

			if mapDoesNotExist(rsMaterial, "refr_trans_weight"):
				if mapDoesNotExist(rsMaterial, "refr_trans_color"):
					transl_weight = getProperty(rsMaterial, "refr_trans_weight")
					transl_color = getProperty(rsMaterial, "refr_trans_color")
					avg_color = sum(transl_color) / 3.0
					if transl_weight <= 0.5:
						if avg_color < transl_weight:
							backscatteringWeight = avg_color
						else:
							backscatteringWeight = transl_weight
					elif transl_weight > 0.5:
						if avg_color < transl_weight and avg_color * 2 <= 1:
							backscatteringWeight = avg_color * 2
						elif transl_weight * 2 <= 1:
							backscatteringWeight = transl_weight * 2
						else:
							backscatteringWeight = 1

					if mapDoesNotExist(rsMaterial, "cutout_opacity"):
						setProperty(rprMaterial, "backscatteringWeight", backscatteringWeight)
					else:
						arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
						setProperty(arithmetic, "operation", 2)
						setProperty(arithmetic, "inputAX", backscatteringWeight)
						copyProperty(arithmetic, rsMaterial, "inputBX", "cutout_opacity")
						connectProperty(arithmetic, "outX", rprMaterial, "backscatteringWeight")

				else:
					if mapDoesNotExist(rsMaterial, "cutout_opacity"):
						setProperty(rprMaterial, "backscatteringWeight", 0.5 * getProperty(rsMaterial, "refr_trans_weight"))
					else:
						arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
						setProperty(arithmetic, "operation", 2)
						copyProperty(arithmetic, rsMaterial, "inputAX", "refr_trans_weight")
						copyProperty(arithmetic, rsMaterial, "inputBX", "cutout_opacity")
						connectProperty(arithmetic, "outX", rprMaterial, "backscatteringWeight")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 2)
				copyProperty(arithmetic, rsMaterial, "inputAX", "refr_trans_weight")
				if mapDoesNotExist(rsMaterial, "cutout_opacity"):
					setProperty(arithmetic, "inputB", (0.5, 0.5, 0.5))
				else:
					copyProperty(arithmetic, rsMaterial, "inputB", "cutout_opacity")
				connectProperty(arithmetic, "outX", rprMaterial, "backscatteringWeight")

			# trans color
			arithmetic1 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic1, "operation", 2)
			copyProperty(arithmetic1, rsMaterial, "inputA", "refr_trans_color")
			setProperty(arithmetic1, "inputB", (2.2, 2.2, 2.2))

			arithmetic2 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic2, "operation", 2)
			copyProperty(arithmetic2, rsMaterial, "inputA", "diffuse")
			setProperty(arithmetic2, "inputB", (2.2, 2.2, 2.2))

			arithmetic3 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic3, "operation", 20)
			connectProperty(arithmetic1, "out", arithmetic3, "inputA")
			connectProperty(arithmetic2, "out", arithmetic3, "inputB")

			connectProperty(arithmetic3, "out", rprMaterial, "backscatteringColor")

		opacity = getProperty(rsMaterial, "cutout_opacity")
		if not opacity:
			if mapDoesNotExist(rsMaterial, "cutout_opacity"):
				transparency = 1 - getProperty(rsMaterial, "cutout_opacity")
				setProperty(rprMaterial, "transparencyLevel", transparency)
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputBX", "cutout_opacity")
				connectProperty(arithmetic, "outX", rprMaterial, "transparencyLevel")
			setProperty(rprMaterial, "transparencyEnable", 1)

		bumpConnections = cmds.listConnections(rsMaterial + ".bump_input")
		if bumpConnections:
			setProperty(rprMaterial, "normalMapEnable", 1)
			copyProperty(rprMaterial, rsMaterial, "normalMap", "bump_input")
			setProperty(rprMaterial, "useShaderNormal", not getProperty(rsMaterial, "no_diffuse_bump"))
			setProperty(rprMaterial, "reflectUseShaderNormal", not getProperty(rsMaterial, "no_refl0_bump"))
			setProperty(rprMaterial, "refractUseShaderNormal", not getProperty(rsMaterial, "no_refr_bump"))
			setProperty(rprMaterial, "coatUseShaderNormal", not getProperty(rsMaterial, "no_refl1_bump"))
				
		# Logging in file
		end_log(rsMaterial)

	if source:
		rprMaterial += "." + source
	return rprMaterial


#######################
## RedshiftSprite 
#######################

def convertRedshiftSprite(rsMaterial, source):

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		input_material = cmds.listConnections(rsMaterial + ".input")[0]
		rprMaterial = convertRedshiftMaterial(input_material, "")[0:-1]
		sg = rprMaterial + "SG"
		cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
		connectProperty(rprMaterial, "outColor", sg, "surfaceShader")
			
		# Logging to file
		start_log(rsMaterial, rprMaterial)

		# Fields conversion

		# convert map
		if getProperty(rsMaterial, "tex0"):

			file = cmds.shadingNode("file", asTexture=True, isColorManaged=True)
			texture = cmds.shadingNode("place2dTexture", asUtility=True)

			connectProperty(texture, "coverage", file, "coverage")
			connectProperty(texture, "translateFrame", file, "translateFrame")
			connectProperty(texture, "rotateFrame", file, "rotateFrame")
			connectProperty(texture, "mirrorU", file, "mirrorU")
			connectProperty(texture, "mirrorV", file, "mirrorV")
			connectProperty(texture, "stagger", file, "stagger")
			connectProperty(texture, "wrapU", file, "wrapU")
			connectProperty(texture, "wrapV", file, "wrapV")
			connectProperty(texture, "repeatUV", file, "repeatUV")
			connectProperty(texture, "offset", file, "offset")
			connectProperty(texture, "rotateUV", file, "rotateUV")
			connectProperty(texture, "noiseUV", file, "noiseUV")
			connectProperty(texture, "vertexUvOne", file, "vertexUvOne")
			connectProperty(texture, "vertexUvTwo", file, "vertexUvTwo")
			connectProperty(texture, "vertexUvThree", file, "vertexUvThree")
			connectProperty(texture, "vertexCameraOne", file, "vertexCameraOne")
			connectProperty(texture, "outUV", file, "uv")
			connectProperty(texture, "outUvFilterSize", file, "uvFilterSize")
			copyProperty(texture, rsMaterial, "repeatU", "repeats0")
			copyProperty(texture, rsMaterial, "repeatV", "repeats1")

			setProperty(file, "fileTextureName", getProperty(rsMaterial, "tex0"))
			arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic, "operation", 1)
			setProperty(arithmetic, "inputA", (1, 1, 1))
			connectProperty(file, "outColor", arithmetic, "inputB")
			connectProperty(arithmetic, "outX", rprMaterial, "transparencyLevel")	
			setProperty(rprMaterial, "transparencyEnable", 1)


		# Logging in file
		end_log(rsMaterial)

	if source:
		rprMaterial += "." + source
	return rprMaterial


#######################
## RedshiftCarPaint 
#######################

def convertRedshiftCarPaint(rsMaterial, source):

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRUberMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")

		# Enable properties, which are default in Redshift
		defaultEnable(rprMaterial, rsMaterial, "diffuse", "diffuse_weight")
		defaultEnable(rprMaterial, rsMaterial, "reflections", "spec_weight")
		defaultEnable(rprMaterial, rsMaterial, "clearCoat", "clearcoat_weight")

		# Logging to file
		start_log(rsMaterial, rprMaterial)

		# Fields conversion

		copyProperty(rprMaterial, rsMaterial, "diffuseColor", "base_color")
		copyProperty(rprMaterial, rsMaterial, "diffuseWeight", "diffuse_weight")

		'''
		blend_value = cmds.shadingNode("RPRBlendValue", asUtility=True)
		connectProperty(blend_value, "out", rprMaterial, "diffuseColor")
		copyProperty(blend_value, rsMaterial, "inputA", "base_color")
		copyProperty(blend_value, rsMaterial, "inputB", "edge_color")

		edge_color_bias = getProperty(rsMaterial, "edge_color_bias")
		if edge_color_bias > 1:
			arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic, "operation", 15)
			setProperty(arithmetic, "inputB", (2, 2, 2))
			connectProperty(arithmetic, "outX", blend_value, "weight")

			fresnel = cmds.shadingNode("RPRFresnel", asUtility=True)
			if edge_color_bias > 5:
				edge_color_bias = 5
			ior = remap_value(edge_color_bias, 5.0, 1.0, 1.1, 5)
			setProperty(fresnel, "ior", ior)
			connectProperty(fresnel, "out", arithmetic, "inputA")

		else:
			sub_arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(sub_arithmetic, "operation", 1)
			setProperty(sub_arithmetic, "inputA", (1, 1, 1))
			copyProperty(sub_arithmetic, rsMaterial, "inputB", "edge_color_bias")

			mult_arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(mult_arithmetic, "operation", 2)
			setProperty(mult_arithmetic, "inputB", (7, 7, 7))
			connectProperty(sub_arithmetic, "out", mult_arithmetic, "inputA")

			dot_arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(dot_arithmetic, "operation", 11)
			connectProperty(mult_arithmetic, "out", dot_arithmetic, "inputB")

			fresnel = cmds.shadingNode("RPRFresnel", asUtility=True)
			setProperty(fresnel, "ior", 1.5)
			connectProperty(fresnel, "out", dot_arithmetic, "inputA")

			connectProperty(dot_arithmetic, "outX", blend_value, "weight")
		'''

		setProperty(rprMaterial, "diffuseRoughness", 0.5)

		copyProperty(rprMaterial, rsMaterial, "reflectColor", "spec_color")
		copyProperty(rprMaterial, rsMaterial, "reflectWeight", "spec_weight")
		'''
		refl_arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
		setProperty(refl_arithmetic, "operation", 20)
		copyProperty(refl_arithmetic, rsMaterial, "inputA", "base_color")
		copyProperty(refl_arithmetic, rsMaterial, "inputB", "flake_color")
		connectProperty(refl_arithmetic, "out", rprMaterial, "reflectColor")

		copyProperty(rprMaterial, rsMaterial, "reflectWeight", "spec_weight")
		
		if mapDoesNotExist(rsMaterial, "spec_gloss"):  
			gloss = 1 - getProperty(rsMaterial, "spec_gloss")
			setProperty(rprMaterial, "reflectRoughness", gloss)
		else:
			if cmds.objectType(cmds.listConnections(rsMaterial + ".spec_gloss")[0]) == "reverse":
				copyProperty(rprMaterial, rsMaterial, "reflectRoughness", "spec_gloss")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputBX", "spec_gloss")
				connectProperty(arithmetic, "outX", rprMaterial, "reflectRoughness")

		spec_facingweight = getProperty(rsMaterial, "spec_facingweight")
		refl_ior = -1 * (spec_facingweight + 1 + 2 * math.sqrt(spec_facingweight)) / (spec_facingweight - 1)
		setProperty(rprMaterial, "reflectIOR", refl_ior)
		'''

		if mapDoesNotExist(rsMaterial, "clearcoat_gloss"):  
			gloss = 1 - getProperty(rsMaterial, "clearcoat_gloss")
			setProperty(rprMaterial, "coatRoughness", gloss)
		else:
			if cmds.objectType(cmds.listConnections(rsMaterial + ".clearcoat_gloss")[0]) == "reverse":
				copyProperty(rprMaterial, rsMaterial, "coatRoughness", "clearcoat_gloss")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputBX", "clearcoat_gloss")
				connectProperty(arithmetic, "outX", rprMaterial, "coatRoughness")

		clearcoat_facingweight = getProperty(rsMaterial, "clearcoat_facingweight")
		coat_ior = -1 * (clearcoat_facingweight + 1 + 2 * math.sqrt(clearcoat_facingweight)) / (clearcoat_facingweight - 1)
		setProperty(rprMaterial, "coatIor", coat_ior)

		copyProperty(rprMaterial, rsMaterial, "coatWeight", "clearcoat_weight")
		copyProperty(rprMaterial, rsMaterial, "coatColor", "clearcoat_color")

		bumpConnections = cmds.listConnections(rsMaterial + ".bump_input")
		if bumpConnections:
			setProperty(rprMaterial, "normalMapEnable", 1)
			copyProperty(rprMaterial, rsMaterial, "normalMap", "bump_input")

			if getProperty(rsMaterial, "no_baselayer_bump"):
				setProperty(rprMaterial, "useShaderNormal", 0)
			else:
				setProperty(rprMaterial, "useShaderNormal", 1)

			if getProperty(rsMaterial, "no_clearcoat_bump"):
				setProperty(rprMaterial, "coatUseShaderNormal", 0)
			else:
				setProperty(rprMaterial, "coatUseShaderNormal", 1)

			setProperty(rprMaterial, "reflectUseShaderNormal", 1)
			setProperty(rprMaterial, "refractUseShaderNormal", 1)

		

		# Logging in file
		end_log(rsMaterial)

	if source:
		rprMaterial += "." + source
	return rprMaterial


######################## 
## RedshiftIncandescent 
########################

def convertRedshiftIncandescent(rsMaterial, source):

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRUberMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")

		# Enable properties, which are default in RedShift
		setProperty(rprMaterial, "diffuse", 0)
		defaultEnable(rprMaterial, rsMaterial, "emissive", "intensity")

		# Logging to file
		start_log(rsMaterial, rprMaterial)

		# Fields conversion
		copyProperty(rprMaterial, rsMaterial, "emissiveIntensity", "intensity")
		copyProperty(rprMaterial, rsMaterial, "emissiveWeight", "alpha")

		setProperty(rprMaterial, "emissiveDoubleSided", getProperty(rsMaterial, "doublesided"))

		if mapDoesNotExist(rsMaterial, "alpha"):
			if getProperty(rsMaterial, "alpha") != 1:
				transparency = 1 - getProperty(rsMaterial, "alpha")
				setProperty(rprMaterial, "transparencyLevel", transparency)
				setProperty(rprMaterial, "transparencyEnable", 1)
		else:
			arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic, "operation", 1)
			setProperty(arithmetic, "inputA", (1, 1, 1))
			copyProperty(arithmetic, rsMaterial, "inputBX", "alpha")
			connectProperty(arithmetic, "outX", rprMaterial, "transparencyLevel")
			setProperty(rprMaterial, "transparencyEnable", 1)
		

		# converting temperature to emissive color
		# no_rpr_analog
		color_mode = getProperty(rsMaterial, "colorMode")
		if color_mode:
			temperature = getProperty(rsMaterial, "temperature") / 100

			if temperature <= 66:
				colorR = 255
			else:
				colorR = temperature - 60
				colorR = 329.698727446 * colorR ** -0.1332047592
				if colorR < 0:
					colorR = 0
				if colorR > 255:
					colorR = 255


			if temperature <= 66:
				colorG = temperature
				colorG = 99.4708025861 * math.log(colorG) - 161.1195681661
				if colorG < 0:
					colorG = 0
				if colorG > 255:
					colorG = 255
			else:
				colorG = temperature - 60
				colorG = 288.1221695283 * colorG ** -0.0755148492
				if colorG < 0:
					colorG = 0
				if colorG > 255:
					colorG = 255


			if temperature >= 66:
				colorB = 255
			elif temperature <= 19:
				colorB = 0
			else:
				colorB = temperature - 10
				colorB = 138.5177312231 * math.log(colorB) - 305.0447927307
				if colorB < 0:
					colorB = 0
				if colorB > 255:
					colorB = 255

			colorR = colorR / 255
			colorG = colorG / 255
			colorB = colorB / 255

			setProperty(rprMaterial, "emissiveColor", (colorR, colorG, colorB))

		else:
			copyProperty(rprMaterial, rsMaterial, "emissiveColor", "color")

		# Logging to file
		end_log(rsMaterial)

	if source:
		rprMaterial += "." + source
	return rprMaterial



###################### 
## RedshiftMaterial 
###################### 

def convertRedshiftMaterial(rsMaterial, source):

	assigned = checkAssign(rsMaterial)
	# duct tape
	if source != "bump_blender":
		listAttr = cmds.listAttr(rsMaterial)
		for attr in listAttr:
			connection = cmds.listConnections(rsMaterial + "." + attr)
			if connection:
				if cmds.objectType(connection[0]) == "RedshiftBumpBlender" and attr == "bump_input" and assigned:
					convertRedshiftBumpBlender(connection[0], "bump_input")
					return

	if cmds.objExists(rsMaterial + "_rpr") and source not in ("bump_blender", "displacement_copy"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRUberMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")

			# displacement conversion
			if source != "displacement_copy":
				rs_sg = cmds.listConnections(rsMaterial, type="shadingEngine")
				displacement = cmds.listConnections(rs_sg, type="RedshiftDisplacement")
				if displacement:
					displacement_file = cmds.listConnections(displacement[0], type="file")
					if displacement_file:
						convertDisplacement(displacement[0], displacement_file[0], rsMaterial, rprMaterial)

		# Enable properties, which are default in RedShift.
		defaultEnable(rprMaterial, rsMaterial, "diffuse", "diffuse_weight")
		defaultEnable(rprMaterial, rsMaterial, "reflections", "refl_weight")
		defaultEnable(rprMaterial, rsMaterial, "refraction", "refr_weight")
		defaultEnable(rprMaterial, rsMaterial, "clearCoat", "coat_weight")
		defaultEnable(rprMaterial, rsMaterial, "emissive", "emission_weight")
		defaultEnable(rprMaterial, rsMaterial, "sssEnable", "ms_amount")

		# Logging to file
		start_log(rsMaterial, rprMaterial)

		# Fields conversion
		copyProperty(rprMaterial, rsMaterial, "diffuseColor", "diffuse_color")
		copyProperty(rprMaterial, rsMaterial, "diffuseWeight", "diffuse_weight")
		copyProperty(rprMaterial, rsMaterial, "diffuseRoughness", "diffuse_roughness")

		copyProperty(rprMaterial, rsMaterial, "reflectWeight", "refl_weight")
		copyProperty(rprMaterial, rsMaterial, "reflectRoughness", "refl_roughness")
		copyProperty(rprMaterial, rsMaterial, "reflectAnisotropy", "refl_aniso")
		copyProperty(rprMaterial, rsMaterial, "reflectAnisotropyRotation", "refl_aniso_rotation")

		# Fresnel type conversion
		refl_reflectivity = getProperty(rsMaterial, "refl_reflectivity")
		refl_fr_mode = getProperty(rsMaterial, "refl_fresnel_mode" )

		if refl_fr_mode == 3:
			copyProperty(rprMaterial, rsMaterial, "reflectIOR", "refl_ior")
			if not mapDoesNotExist(rsMaterial, "refl_color"):
				connection = cmds.listConnections(rsMaterial + ".refl_color", type="file")
				if connection:
					setProperty(connection[0], "colorSpace", "Raw")
			copyProperty(rprMaterial, rsMaterial, "reflectColor", "refl_color")

		elif refl_fr_mode == 2:

			blend_value = cmds.shadingNode("RPRBlendValue", asUtility=True)
			connectProperty(blend_value, "out", rprMaterial, "reflectColor")

			# blend color from diffuse and reflectivity to reflect color
			# no_rpr_analog

			copyProperty(blend_value, rsMaterial, "inputA", "refl_reflectivity")
			copyProperty(blend_value, rsMaterial, "inputB", "diffuse_color")
			copyProperty(blend_value, rsMaterial, "weight", "refl_metalness")

			metalness = getProperty(rsMaterial, "refl_metalness")
			if metalness > 0:
				setProperty(rprMaterial, "reflectMetalMaterial", 1)
				copyProperty(rprMaterial, rsMaterial, "reflectMetalness", "refl_metalness")

		# no_rpr_analog
		elif refl_fr_mode == 1:

			edge_tint = getProperty(rsMaterial, "refl_edge_tint")

			arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
			connectProperty(arithmetic, "out", rprMaterial, "reflectColor")

			blend_value = cmds.shadingNode("RPRBlendValue", asUtility=True)
			connectProperty(blend_value, "out", arithmetic, "inputB")

			fresnel = cmds.shadingNode("RPRFresnel", asUtility=True)
			connectProperty(fresnel, "out", blend_value, "weight")

			if not mapDoesNotExist(rsMaterial, "refl_color"):
				connection = cmds.listConnections(rsMaterial + ".refl_color", type="file")
				if connection:
					setProperty(connection[0], "colorSpace", "Raw")
			copyProperty(arithmetic, rsMaterial, "inputA", "refl_color")

			setProperty(arithmetic, "operation", 2)

			setProperty(fresnel, "ior", 1.5)

			if edge_tint[0] or edge_tint[1] or edge_tint[2]:

				copyProperty(blend_value, rsMaterial, "inputA", "refl_reflectivity")
				copyProperty(blend_value, rsMaterial, "inputB", "refl_edge_tint")

				setProperty(rprMaterial, "reflectMetalMaterial", 1)
				copyProperty(rprMaterial, rsMaterial, "reflectMetalness", "refl_metalness")
				if not getProperty(rprMaterial, "reflectMetalness"):
					setProperty(rprMaterial, "reflectMetalness", 1)

			else:

				copyProperty(blend_value, rsMaterial, "inputA", "refl_reflectivity")

				if not mapDoesNotExist(rsMaterial, "refl_color"):
					connection = cmds.listConnections(rsMaterial + ".refl_color", type="file")
					if connection:
						setProperty(connection[0], "colorSpace", "Raw")
				copyProperty(blend_value, rsMaterial, "inputB", "refl_color")

				max_refl = max(refl_reflectivity)
				if max_refl == 1:
					max_refl = 0.9999
				elif max_refl == 0:
					max_refl = 0.0001

				ior = -1 * (max_refl + 1 + 2 * math.sqrt(max_refl) / (max_refl - 1))
				if ior > 10:
					ior = 10

				setProperty(rprMaterial, "reflectIOR", ior)
				

		else:
			# advanced ior
			# no_rpr_analog
			# take one channel from advanced ior ti rpr ior
			copyProperty(rprMaterial, rsMaterial, "reflectIOR", "refl_ior30")
			if not mapDoesNotExist(rsMaterial, "refl_color"):
				connection = cmds.listConnections(rsMaterial + ".refl_color", type="file")
				if connection:
					setProperty(connection[0], "colorSpace", "Raw")
			copyProperty(rprMaterial, rsMaterial, "reflectColor", "refl_color")

		copyProperty(rprMaterial, rsMaterial, "refractColor", "refr_color")
		copyProperty(rprMaterial, rsMaterial, "refractWeight", "refr_weight")
		copyProperty(rprMaterial, rsMaterial, "refractRoughness", "refr_roughness")
		copyProperty(rprMaterial, rsMaterial, "refractIor", "refr_ior")
		copyProperty(rprMaterial, rsMaterial, "refractLinkToReflect", "refr_use_base_IOR")
		copyProperty(rprMaterial, rsMaterial, "refractThinSurface", "refr_thin_walled")

		# maps doesn't support ( will work incorrectly )
		ss_unitsMode = getProperty(rsMaterial, "ss_unitsMode")
		if ss_unitsMode:
			if mapDoesNotExist(rsMaterial, "ss_extinction_coeff"):
				ss_ext_coeff = getProperty(rsMaterial, "ss_extinction_coeff")
				absorb_color = (1 - ss_ext_coeff[0], 1 - ss_ext_coeff[1], 1 - ss_ext_coeff[2])
				setProperty(rprMaterial, "refractAbsorbColor", absorb_color)

			if mapDoesNotExist(rsMaterial, "ss_extinction_scale"):
				if getProperty(rsMaterial, "ss_extinction_scale"):
					absorption = 1 / getProperty(rsMaterial,  "ss_extinction_scale")
					setProperty(rprMaterial, "refractAbsorptionDistance", absorption)
		else:
			copyProperty(rprMaterial, rsMaterial, "refractAbsorbColor", "refr_transmittance")
			if mapDoesNotExist(rsMaterial, "refr_absorption_scale"):
				if getProperty(rsMaterial, "refr_absorption_scale"):
					absorption = 1 / getProperty(rsMaterial, "refr_absorption_scale")
					setProperty(rprMaterial, "refractAbsorptionDistance", absorption)

		copyProperty(rprMaterial, rsMaterial, "coatColor", "coat_color")
		copyProperty(rprMaterial, rsMaterial, "coatWeight", "coat_weight")
		copyProperty(rprMaterial, rsMaterial, "coatRoughness", "coat_roughness")
		copyProperty(rprMaterial, rsMaterial, "coatTransmissionColor", "coat_transmittance")

		coat_fr_mode = getProperty(rsMaterial, "coat_fresnel_mode")
		if coat_fr_mode == 3:
			copyProperty(rprMaterial, rsMaterial, "coatIor", "coat_ior")

		copyProperty(rprMaterial, rsMaterial, "emissiveColor", "emission_color")
		copyProperty(rprMaterial, rsMaterial, "emissiveWeight", "emission_weight")
		copyProperty(rprMaterial, rsMaterial, "emissiveIntensity", "emission_weight")

		copyProperty(rprMaterial, rsMaterial, "backscatteringWeight", "ms_amount")
		copyProperty(rprMaterial, rsMaterial, "sssWeight", "ms_amount")

		backscatteringWeight = getProperty(rsMaterial, "transl_weight")

		# SSS
		ms_amount = getProperty(rsMaterial, "ms_amount")
		if ms_amount:
			if not backscatteringWeight:
				setProperty(rprMaterial, "backscatteringWeight", 0.5)
				setProperty(rprMaterial, "separateBackscatterColor", 0)

			# first layer
			arithmetic1 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic1, "operation", 2)
			# input A
			if mapDoesNotExist(rsMaterial, "ms_color0"):
				copyProperty(arithmetic1, rsMaterial, "inputA", "ms_color0")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 15)
				copyProperty(arithmetic, rsMaterial, "inputA", "ms_color0")
				setProperty(arithmetic, "inputB", (2, 2, 2))
				connectProperty(arithmetic, "out", arithmetic1, "inputA")
			# input B
			factor1 = 2 * getProperty(rsMaterial, "ms_weight0") * getProperty(rsMaterial, "ms_radius0") * getProperty(rsMaterial, "ms_radius_scale")
			setProperty(arithmetic1, "inputB", (factor1, factor1, factor1))

			# second layer
			# divide L2 by 2
			arithmetic_divide1 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic_divide1, "operation", 3)
			copyProperty(arithmetic_divide1, rsMaterial, "inputA", "ms_color1")
			setProperty(arithmetic_divide1, "inputB", (2, 2, 2))

			# pow 2
			arithmetic2 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic2, "operation", 2)
			# input A
			if mapDoesNotExist(rsMaterial, "ms_color1"):
				connectProperty(arithmetic_divide1, "out", arithmetic2, "inputA")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 15)
				connectProperty(arithmetic_divide1, "out", arithmetic, "inputA")
				setProperty(arithmetic, "inputB", (2, 2, 2))
				connectProperty(arithmetic, "out", arithmetic2, "inputA")
			# input B
			factor2 = 2 * getProperty(rsMaterial, "ms_weight1") * getProperty(rsMaterial, "ms_radius1") * getProperty(rsMaterial, "ms_radius_scale")
			setProperty(arithmetic2, "inputB", (factor2, factor2, factor2))	

			# third layer
			# divide L3 by 4
			arithmetic_divide2 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic_divide2, "operation", 3)
			copyProperty(arithmetic_divide2, rsMaterial, "inputA", "ms_color2")
			setProperty(arithmetic_divide2, "inputB", (4, 4, 4))

			# pow 2
			arithmetic3 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic3, "operation", 2)
			# input A
			if mapDoesNotExist(rsMaterial, "ms_color2"):
				connectProperty(arithmetic_divide2, "out", arithmetic3, "inputA")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 15)
				connectProperty(arithmetic_divide2, "out", arithmetic3, "inputA")
				setProperty(arithmetic, "inputB", (2, 2, 2))
				connectProperty(arithmetic, "out", arithmetic3, "inputA")
			# input B
			factor3 = 2 * getProperty(rsMaterial, "ms_weight2") * getProperty(rsMaterial, "ms_radius2") * getProperty(rsMaterial, "ms_radius_scale")
			setProperty(arithmetic3, "inputB", (factor3, factor3, factor3))

			arithmetic_mix_1 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic_mix_1, "operation", 20)
			connectProperty(arithmetic1, "out", arithmetic_mix_1, "inputA")
			connectProperty(arithmetic2, "out", arithmetic_mix_1, "inputB")

			arithmetic_mix_2 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic_mix_2, "operation", 20)
			connectProperty(arithmetic_mix_1, "out", arithmetic_mix_2, "inputA")
			connectProperty(arithmetic3, "out", arithmetic_mix_2, "inputB")
			connectProperty(arithmetic_mix_2, "out", rprMaterial, "subsurfaceRadius")

			arithmetic_mix_3 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic_mix_3, "operation", 20)
			copyProperty(arithmetic_mix_3, rsMaterial, "inputA", "ms_color0")
			connectProperty(arithmetic_divide1, "out", arithmetic_mix_3, "inputB")

			arithmetic_mix_4 = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(arithmetic_mix_4, "operation", 20)
			connectProperty(arithmetic_mix_3, "out", arithmetic_mix_4, "inputA")
			connectProperty(arithmetic_divide2, "out", arithmetic_mix_4, "inputB")
			connectProperty(arithmetic_mix_4, "out", rprMaterial, "volumeScatter")

		# transl
		if backscatteringWeight:
			setProperty(rprMaterial, "separateBackscatterColor", 1)

			if mapDoesNotExist(rsMaterial, "transl_weight"):
				if mapDoesNotExist(rsMaterial, "transl_color"):
					transl_weight = getProperty(rsMaterial, "transl_weight")
					transl_color = getProperty(rsMaterial, "transl_color")
					avg_color = sum(transl_color) / 3.0
					if transl_weight <= 0.5:
						if avg_color < transl_weight:
							backscatteringWeight = avg_color
						else:
							backscatteringWeight = transl_weight
					elif transl_weight > 0.5:
						if avg_color < transl_weight and avg_color * 2 <= 1:
							backscatteringWeight = avg_color * 2
						elif transl_weight * 2 <= 1:
							backscatteringWeight = transl_weight * 2
						else:
							backscatteringWeight = 1

					if mapDoesNotExist(rsMaterial, "opacity_color"):
						setProperty(rprMaterial, "backscatteringWeight", backscatteringWeight)
					else:
						arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
						setProperty(arithmetic, "operation", 2)
						setProperty(arithmetic, "inputAX", backscatteringWeight)
						copyProperty(arithmetic, rsMaterial, "inputB", "opacity_color")
						connectProperty(arithmetic, "outX", rprMaterial, "backscatteringWeight")

				else:
					if mapDoesNotExist(rsMaterial, "opacity_color"):
						setProperty(rprMaterial, "backscatteringWeight", 0.5 * getProperty(rsMaterial, "transl_weight"))
					else:
						arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
						setProperty(arithmetic, "operation", 2)
						copyProperty(arithmetic, rsMaterial, "inputAX", "transl_weight")
						copyProperty(arithmetic, rsMaterial, "inputB", "opacity_color")
						connectProperty(arithmetic, "outX", rprMaterial, "backscatteringWeight")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 2)
				copyProperty(arithmetic, rsMaterial, "inputAX", "transl_weight")
				if mapDoesNotExist(rsMaterial, "opacity_color"):
					setProperty(arithmetic, "inputB", (0.5, 0.5, 0.5))
				else:
					copyProperty(arithmetic, rsMaterial, "inputB", "opacity_color")
				connectProperty(arithmetic, "outX", rprMaterial, "backscatteringWeight")

			if mapDoesNotExist(rsMaterial, "transl_color"):
				transl_color = getProperty(rsMaterial, "transl_color")
				arithmetic1 = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic1, "operation", 0)
				setProperty(arithmetic1, "inputA", transl_color)
				remap_color = []
				for i in range(len(transl_color)):
					remap_color.append(remap_value(transl_color[i], 1.0, 0.0, 0.0, 0.7))
				setProperty(arithmetic1, "inputB", tuple(remap_color))

				arithmetic2 = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic2, "operation", 2)
				setProperty(arithmetic2, "inputA", transl_color)
				setProperty(arithmetic2, "inputB", (2.2, 2.2, 2.2))

				arithmetic3 = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic3, "operation", 2)
				connectProperty(arithmetic1, "out", arithmetic3, "inputA")
				connectProperty(arithmetic2, "out", arithmetic3, "inputB")

				connectProperty(arithmetic3, "out", rprMaterial, "backscatteringColor")
			else:
				arithmetic1 = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic1, "operation", 0)
				copyProperty(arithmetic1, rsMaterial, "inputA", "transl_color")
				copyProperty(arithmetic1, rprMaterial, "inputBX", "backscatteringWeight")
				copyProperty(arithmetic1, rprMaterial, "inputBY", "backscatteringWeight")
				copyProperty(arithmetic1, rprMaterial, "inputBZ", "backscatteringWeight")

				arithmetic2 = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic2, "operation", 2)
				copyProperty(arithmetic2, rsMaterial, "inputA", "transl_color")
				setProperty(arithmetic2, "inputB", (1.5, 1.5, 1.5))

				arithmetic3 = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic3, "operation", 2)
				connectProperty(arithmetic1, "out", arithmetic3, "inputA")
				connectProperty(arithmetic2, "out", arithmetic3, "inputB")

				connectProperty(arithmetic3, "out", rprMaterial, "backscatteringColor")

		if getProperty(rsMaterial, "opacity_color") != (1, 1, 1):
			if mapDoesNotExist(rsMaterial, "opacity_color"):
				transparency = 1 - max(getProperty(rsMaterial, "opacity_color"))
				setProperty(rprMaterial, "transparencyLevel", transparency)
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputB", "opacity_color")
				connectProperty(arithmetic, "outX", rprMaterial, "transparencyLevel")
			setProperty(rprMaterial, "transparencyEnable", 1)

		# duct tape
		if source != "bump_blender":
			bumpConnections = cmds.listConnections(rsMaterial + ".bump_input")
			if bumpConnections:
				setProperty(rprMaterial, "normalMapEnable", 1)
				copyProperty(rprMaterial, rsMaterial, "normalMap", "bump_input")
				setProperty(rprMaterial, "useShaderNormal", 1)
				setProperty(rprMaterial, "reflectUseShaderNormal", 1)
				setProperty(rprMaterial, "refractUseShaderNormal", 1)
				setProperty(rprMaterial, "coatUseShaderNormal", 1)
		
		# Logging to file
		end_log(rsMaterial)

	if source and source not in ("bump_blender", "displacement_copy"):
		rprMaterial += "." + source
	return rprMaterial


##########################
## RedshiftMaterialBlender 
##########################

def convertRedshiftMaterialBlender(rsMaterial, source): 

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRBlendMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")

		# Logging to file
		start_log(rsMaterial, rprMaterial)  

		# Fields conversion
		copyProperty(rprMaterial, rsMaterial, "color0", "baseColor")
		copyProperty(rprMaterial, rsMaterial, "color1", "layerColor1")

		# weight conversion
		weight = cmds.listConnections(rsMaterial + ".blendColor1")
		if weight:
			connectProperty(weight[0], "outAlpha", rprMaterial, "weight")

		# Logging to file
		end_log(rsMaterial) 

	if source:
		rprMaterial += "." + source
	return rprMaterial


#######################
## RedshiftSkin
#######################

def convertRedshiftSkin(rsMaterial, source):

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRUberMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")

		# Enable properties, which are default in Redshift
		defaultEnable(rprMaterial, rsMaterial, "reflections", "refl_weight0")
		defaultEnable(rprMaterial, rsMaterial, "clearCoat", "refl_weight1")

		# Logging to file
		start_log(rsMaterial, rprMaterial)

		# Fields conversion
		setProperty(rprMaterial, "diffuseWeight", 1)
		setProperty(rprMaterial, "diffuseRoughness", 0)
		setProperty(rprMaterial, "separateBackscatterColor", True)
		setProperty(rprMaterial, "backscatteringWeight", 0.4)
		copyProperty(rprMaterial, rsMaterial, "reflectColor", "refl_color0")
		copyProperty(rprMaterial, rsMaterial, "reflectWeight", "refl_weight0")
		setProperty(rprMaterial, "reflectRoughness", (1 - getProperty(rsMaterial, "refl_gloss0")))
		copyProperty(rprMaterial, rsMaterial, "reflectIOR", "refl_ior0")
		copyProperty(rprMaterial, rsMaterial, "coatColor", "refl_color1")
		copyProperty(rprMaterial, rsMaterial, "coatWeight", "refl_weight1")
		setProperty(rprMaterial, "coatRoughness", (1 - getProperty(rsMaterial, "refl_gloss1")))
		copyProperty(rprMaterial, rsMaterial, "coatIor", "refl_ior1")

		# shallow radius * radius scale
		shallow_raduis_x_radius_scale = cmds.shadingNode("RPRArithmetic", asUtility=True)
		shallow_raduis_x_radius_scale = cmds.rename(shallow_raduis_x_radius_scale, ("shallow_raduis_x_radius_scale"))
		setProperty(shallow_raduis_x_radius_scale, "operation", 2)
		copyProperty(shallow_raduis_x_radius_scale, rsMaterial, "inputAX", "shallow_radius")
		copyProperty(shallow_raduis_x_radius_scale, rsMaterial, "inputBX", "radius_scale")

		# shallow radius * weight
		shallow_raduis_x_weight = cmds.shadingNode("RPRArithmetic", asUtility=True)
		shallow_raduis_x_weight = cmds.rename(shallow_raduis_x_weight, ("shallow_raduis_x_weight"))
		setProperty(shallow_raduis_x_weight, "operation", 2)
		copyProperty(shallow_raduis_x_weight, rsMaterial, "inputAX", "shallow_weight")
		connectProperty(shallow_raduis_x_radius_scale, "out", shallow_raduis_x_weight, "inputB")

		# Mult by OverallScale
		mult_by_overall_scale = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mult_by_overall_scale = cmds.rename(mult_by_overall_scale, ("mult_by_overall_scale"))
		setProperty(mult_by_overall_scale, "operation", 2)
		copyProperty(mult_by_overall_scale, rsMaterial, "inputAX", "overall_scale")
		connectProperty(shallow_raduis_x_weight, "out", mult_by_overall_scale, "inputB")

		# Mult by Shallow Color
		mult_by_shallow_color = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mult_by_shallow_color = cmds.rename(mult_by_shallow_color, ("mult_by_shallow_color"))
		setProperty(mult_by_shallow_color, "operation", 2)
		if mapDoesNotExist(rsMaterial, "shallow_color"):
			copyProperty(mult_by_shallow_color, rsMaterial, "inputA", "shallow_color")
		else:
			shallow_color_map = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(shallow_color_map, "operation", 15)
			copyProperty(shallow_color_map, rsMaterial, "inputA", "shallow_color")
			setProperty(shallow_color_map, "inputB", (2.2, 2.2, 2.2))
			connectProperty(shallow_color_map, "out", mult_by_shallow_color, "inputA")
		connectProperty(mult_by_overall_scale, "out", mult_by_shallow_color, "inputB")

		# middle radius * radius scale
		mid_raduis_x_radius_scale = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mid_raduis_x_radius_scale = cmds.rename(mid_raduis_x_radius_scale, ("mid_raduis_x_radius_scale"))
		setProperty(mid_raduis_x_radius_scale, "operation", 2)
		copyProperty(mid_raduis_x_radius_scale, rsMaterial, "inputAX", "mid_radius")
		copyProperty(mid_raduis_x_radius_scale, rsMaterial, "inputBX", "radius_scale")

		# middle radius * weight
		mid_raduis_x_weight = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mid_raduis_x_weight = cmds.rename(mid_raduis_x_weight, ("mid_raduis_x_weight"))
		setProperty(mid_raduis_x_weight, "operation", 2)
		copyProperty(mid_raduis_x_weight, rsMaterial, "inputAX", "mid_weight")
		connectProperty(mid_raduis_x_radius_scale, "out", mid_raduis_x_weight, "inputB")

		# Mult by OverallScaleMiddle
		mult_by_overall_scale_middle = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mult_by_overall_scale_middle = cmds.rename(mult_by_overall_scale_middle, ("mult_by_overall_scale_middle"))
		setProperty(mult_by_overall_scale, "operation", 2)
		copyProperty(mult_by_overall_scale, rsMaterial, "inputAX", "overall_scale")
		connectProperty(mid_raduis_x_weight, "out", mult_by_overall_scale_middle, "inputB")

		# Mult by Middle Color
		mult_by_middle_color = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mult_by_middle_color = cmds.rename(mult_by_middle_color, ("mult_by_middle_color"))
		setProperty(mult_by_middle_color, "operation", 2)
		if mapDoesNotExist(rsMaterial, "mid_color"):
			copyProperty(mult_by_middle_color, rsMaterial, "inputA", "mid_color")
		else:
			mid_color_map = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(mid_color_map, "operation", 15)
			copyProperty(mid_color_map, rsMaterial, "inputA", "mid_color")
			setProperty(mid_color_map, "inputB", (2.2, 2.2, 2.2))
			connectProperty(mid_color_map, "out", mult_by_middle_color, "inputA")
		connectProperty(mult_by_overall_scale_middle, "out", mult_by_middle_color, "inputB")

		# Mix ShallowBiasedColor and MiddleBiasedColor
		shallow_biased_color_mix_middle_biased_color = cmds.shadingNode("RPRArithmetic", asUtility=True)
		shallow_biased_color_mix_middle_biased_color = cmds.rename(shallow_biased_color_mix_middle_biased_color, ("shallow_biased_color_mix_middle_biased_color"))
		setProperty(shallow_biased_color_mix_middle_biased_color, "operation", 20)
		connectProperty(mult_by_shallow_color, "out", shallow_biased_color_mix_middle_biased_color, "inputA")
		connectProperty(mult_by_middle_color, "out", shallow_biased_color_mix_middle_biased_color, "inputB")

		# deep radius * radius scale
		deep_raduis_x_radius_scale = cmds.shadingNode("RPRArithmetic", asUtility=True)
		deep_raduis_x_radius_scale = cmds.rename(deep_raduis_x_radius_scale, ("deep_raduis_x_radius_scale"))
		setProperty(deep_raduis_x_radius_scale, "operation", 2)
		copyProperty(deep_raduis_x_radius_scale, rsMaterial, "inputAX", "deep_radius")
		copyProperty(deep_raduis_x_radius_scale, rsMaterial, "inputBX", "radius_scale")

		# deep radius * weight
		deep_raduis_x_weight = cmds.shadingNode("RPRArithmetic", asUtility=True)
		deep_raduis_x_weight = cmds.rename(deep_raduis_x_weight, ("deep_raduis_x_weight"))
		setProperty(deep_raduis_x_weight, "operation", 2)
		copyProperty(mid_raduis_x_weight, rsMaterial, "inputAX", "deep_weight")
		connectProperty(deep_raduis_x_radius_scale, "out", deep_raduis_x_weight, "inputB")

		# Mult by OverallScaleDeep
		mult_by_overall_scale_deep = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mult_by_overall_scale_deep = cmds.rename(mult_by_overall_scale_deep, ("mult_by_overall_scale_deep"))
		setProperty(mult_by_overall_scale_deep, "operation", 2)
		copyProperty(mult_by_overall_scale_deep, rsMaterial, "inputAX", "overall_scale")
		connectProperty(deep_raduis_x_weight, "out", mult_by_overall_scale_deep, "inputB")

		# Mult by Deep Color
		mult_by_deep_color = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mult_by_deep_color = cmds.rename(mult_by_deep_color, ("mult_by_deep_color"))
		setProperty(mult_by_deep_color, "operation", 20)
		if mapDoesNotExist(rsMaterial, "deep_color"):
			copyProperty(mult_by_deep_color, rsMaterial, "inputA", "deep_color")
		else:
			deep_color_map = cmds.shadingNode("RPRArithmetic", asUtility=True)
			setProperty(deep_color_map, "operation", 15)
			copyProperty(deep_color_map, rsMaterial, "inputA", "deep_color")
			setProperty(deep_color_map, "inputB", (2.2, 2.2, 2.2))
			connectProperty(deep_color_map, "out", mult_by_deep_color, "inputA")
		connectProperty(mult_by_overall_scale_deep, "out", mult_by_deep_color, "inputB")

		# Mix DeepBiasColor
		mix_deep_bias_color = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mix_deep_bias_color = cmds.rename(mix_deep_bias_color, ("mix_deep_bias_color"))
		setProperty(mix_deep_bias_color, "operation", 20)
		connectProperty(shallow_biased_color_mix_middle_biased_color, "out", mix_deep_bias_color, "inputA")
		connectProperty(mult_by_deep_color, "out", mix_deep_bias_color, "inputB")

		# SSS radius result
		connectProperty(mix_deep_bias_color, "out", rprMaterial, "subsurfaceRadius")

		# Mix ShallowColor and MiddleColor
		shallow_color_mix_middle_color = cmds.shadingNode("RPRArithmetic", asUtility=True)
		shallow_color_mix_middle_color = cmds.rename(shallow_color_mix_middle_color, ("shallow_color_mix_middle_color"))
		setProperty(shallow_color_mix_middle_color, "operation", 20)
		if mapDoesNotExist(rsMaterial, "shallow_color"):
			copyProperty(shallow_color_mix_middle_color, rsMaterial, "inputA", "shallow_color")
		else:
			connectProperty(shallow_color_map, "out", shallow_color_mix_middle_color, "inputA")
		if mapDoesNotExist(rsMaterial, "mid_color"):
			copyProperty(shallow_color_mix_middle_color, rsMaterial, "inputA", "mid_color")
		else:
			connectProperty(mid_color_map, "out", shallow_color_mix_middle_color, "inputB")

		# Mix DeepColor
		mix_deep_color = cmds.shadingNode("RPRArithmetic", asUtility=True)
		mix_deep_color = cmds.rename(mix_deep_color, ("mix_deep_color"))
		setProperty(mix_deep_color, "operation", 20)
		if mapDoesNotExist(rsMaterial, "deep_color"):
			copyProperty(mix_deep_color, rsMaterial, "inputA", "deep_color")
		else:
			connectProperty(deep_color_map, "out", mix_deep_color, "inputA")
		connectProperty(shallow_color_mix_middle_color, "out", mix_deep_color, "inputB")

		# volume scatter
		connectProperty(mix_deep_color, "out", rprMaterial, "volumeScatter")

		# Color Correction
		color_correction = cmds.shadingNode("RPRArithmetic", asUtility=True)
		color_correction = cmds.rename(color_correction, ("color_correction"))
		setProperty(color_correction, "operation", 2)
		connectProperty(mix_deep_color, "out", color_correction, "inputA")
		setProperty(color_correction, "inputB", (1.3, 1.3, 1.3))

		# backscattering color & diffuse color
		connectProperty(color_correction, "out", rprMaterial, "diffuseColor")
		connectProperty(color_correction, "out", rprMaterial, "backscatteringColor")

		# Logging in file
		end_log(rsMaterial)

	if source:
		rprMaterial += "." + source
	return rprMaterial


#############################
## RedshiftMatteShadowCatcher 
#############################

def convertRedshiftMatteShadowCatcher(rsMaterial, source):  

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRShadowCatcherMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")

		# Logging to file
		start_log(rsMaterial, rprMaterial)  

		# Fields conversion
		copyProperty(rprMaterial, rsMaterial, "bgIsEnv", "backgroundIsEnv")
		copyProperty(rprMaterial, rsMaterial, "shadowTransp", "transparency")
		copyProperty(rprMaterial, rsMaterial, "bgColor", "background")
		copyProperty(rprMaterial, rsMaterial, "shadowColor", "shadows")
		
		# Logging to file
		end_log(rsMaterial) 

	if source:
		rprMaterial += "." + source
	return rprMaterial


############################
## RedshiftSubSurfaceScatter 
############################ 

def convertRedshiftSubSurfaceScatter(rsMaterial, source):  

	assigned = checkAssign(rsMaterial)
	
	if cmds.objExists(rsMaterial + "_rpr"):
		rprMaterial = rsMaterial + "_rpr"
	else:
		# Creating new Uber material
		rprMaterial = cmds.shadingNode("RPRUberMaterial", asShader=True)
		rprMaterial = cmds.rename(rprMaterial, (rsMaterial + "_rpr"))

		# Check shading engine in rsMaterial
		if assigned:
			sg = rprMaterial + "SG"
			cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
			connectProperty(rprMaterial, "outColor", sg, "surfaceShader")
			 
		# Enable properties, which are default in RedShift
		if getProperty(rsMaterial, "scatter_radius") >= 0.01:
			setProperty(rprMaterial, "sssEnable", 1)

		scatter_color = getProperty(rsMaterial, "scatter_color")
		if sum(scatter_color) / len(scatter_color) >= 0.01:
			setProperty(rprMaterial, "separateBackscatterColor", 1)

		setProperty(rprMaterial, "reflections", 1)
			
		# Logging to file
		start_log(rsMaterial, rprMaterial)   

		# Fields conversion
		setProperty(rprMaterial, "diffuseWeight", 1)
		setProperty(rprMaterial, "diffuseRoughness", 0)
		setProperty(rprMaterial, "backscatteringWeight", 0.5)
		copyProperty(rprMaterial, rsMaterial, "reflectIOR", "ior")
		copyProperty(rprMaterial, rsMaterial, "volumeScatter", "sub_surface_color")

		sub_surface_color = getProperty(rsMaterial, "sub_surface_color")
		diffuseColor = (clampValue(sub_surface_color[0] * 1.59, 0, 1), clampValue(sub_surface_color[1] * 1.59, 0, 1), clampValue(sub_surface_color[2] * 1.59, 0, 1))
		setProperty(rprMaterial, "diffuseColor", diffuseColor)
		
		if sum(sub_surface_color) / len(sub_surface_color) < 0.255:
			setProperty(rprMaterial, "backscatteringColor", (sub_surface_color[0] * 3.5, sub_surface_color[1] * 3.5, sub_surface_color[2] * 3.5))
		else:
			setProperty(rprMaterial, "backscatteringColor", (sub_surface_color[0] * 1.59, sub_surface_color[1] * 1.59, sub_surface_color[2] * 1.59))

		if mapDoesNotExist(rsMaterial, "scatter_color"):   
			radius = getProperty(rsMaterial, "scatter_radius")
			scatterColor= getProperty(rsMaterial, "scatter_color")
			sssRadius = [radius + scatterColor[0] * 1.5, radius + scatterColor[1], radius + scatterColor[2]]
			setProperty(rprMaterial, "subsurfaceRadius", tuple(sssRadius))

		if mapDoesNotExist(rsMaterial, "refl_gloss"):  
			gloss = 1 - getProperty(rsMaterial, "refl_gloss")
			setProperty(rprMaterial, "reflectRoughness", gloss)
		else:
			if cmds.objectType(cmds.listConnections(rsMaterial + ".refl_gloss")[0]) == "reverse":
				copyProperty(rprMaterial, rsMaterial, "reflectRoughness", "refl_gloss")
			else:
				arithmetic = cmds.shadingNode("RPRArithmetic", asUtility=True)
				setProperty(arithmetic, "operation", 1)
				setProperty(arithmetic, "inputA", (1, 1, 1))
				copyProperty(arithmetic, rsMaterial, "inputBX", "refl_gloss")
				connectProperty(arithmetic, "outX", rprMaterial, "reflectRoughness")
		   
		# Logging to file
		end_log(rsMaterial) 

	if source:
		rprMaterial += "." + source
	return rprMaterial


def convertRedshiftPhysicalSky(rsSky):
	
	# create RPRSky node
	skyNode = cmds.createNode("RPRSky", n="RPRSkyShape")
  
	# Logging to file
	start_log(sky, skyNode)

	# Copy properties from rsPhysicalSky
	setProperty(skyNode, "intensity", getProperty(sky, "multiplier") * 2)
	copyProperty(skyNode, rsSky, "turbidity", "haze")
	copyProperty(skyNode, rsSky, "groundColor", "ground_color")
	copyProperty(skyNode, rsSky, "filterColor", "night_color")
	copyProperty(skyNode, rsSky, "sunDiskSize", "sun_disk_scale")
	copyProperty(skyNode, rsSky, "sunGlow", "sun_glow_intensity")

	# Logging to file
	end_log(sky)  


def convertRedshiftEnvironment(env):

	if cmds.objExists("RPRIBL"):
		iblShape = "RPRIBLShape"
		iblTransform = "RPRIBL"
	else:
		# create IBL node
		iblShape = cmds.createNode("RPRIBL", n="RPRIBLShape")
		iblTransform = cmds.listRelatives(iblShape, p=True)[0]
		setProperty(iblTransform, "scaleX", 1001.25663706144)
		setProperty(iblTransform, "scaleY", 1001.25663706144)
		setProperty(iblTransform, "scaleZ", 1001.25663706144)

	# Logging to file 
	start_log(env, iblShape)
  
	# Copy properties from rsEnvironment
	exposure = getProperty(env, "exposure0")
	setProperty(iblShape, "intensity", 1 * 2 ** exposure)

	copyProperty(iblShape, env, "display", "backPlateEnabled")

	texMode = getProperty(env, "texMode")
	if texMode == 0: # default
		copyProperty(iblTransform, env, "filePath", "tex0")

	envTransform = cmds.listConnections(env, type="place3dTexture")[0]
	copyProperty(iblTransform, envTransform, "rotateX", "rotateX")
	copyProperty(iblTransform, envTransform, "rotateY", "rotateY")
	copyProperty(iblTransform, envTransform, "rotateZ", "rotateZ")

	# Logging to file
	end_log(env)  


def convertRedshiftDomeLight(dome_light):

	if cmds.objExists("RPRIBL"):
		iblShape = "RPRIBLShape"
		iblTransform = "RPRIBL"
	else:
		# create IBL node
		iblShape = cmds.createNode("RPRIBL", n="RPRIBLShape")
		iblTransform = cmds.listRelatives(iblShape, p=True)[0]
		setProperty(iblTransform, "scaleX", 1001.25663706144)
		setProperty(iblTransform, "scaleY", 1001.25663706144)
		setProperty(iblTransform, "scaleZ", 1001.25663706144)

	# Logging to file 
	start_log(dome_light, iblShape)

	# display IBL option
	exposure = getProperty(dome_light, "exposure0")
	setProperty(iblShape, "intensity", 1 * 2 ** exposure)

	copyProperty(iblShape, dome_light, "display", "background_enable")

	setProperty(iblTransform, "filePath", getProperty(dome_light, "tex0"))
	
	domeTransform = cmds.listRelatives(dome_light, p=True)[0]
	rotateY = getProperty(domeTransform, "rotateY") - 90
	setProperty(iblTransform, "rotateY", rotateY)

	# Logging to file
	end_log(dome_light)  


def convertRedshiftPhysicalLight(rs_light):

	# Redshift light transform
	splited_name = rs_light.split("|")
	rsTransform = "|".join(splited_name[0:-1])
	group = "|".join(splited_name[0:-2])

	if cmds.objExists(rsTransform + "_rpr"):
		rprTransform = rsTransform + "_rpr"
		rprLightShape = cmds.listRelatives(rprTransform)[0]
	else: 
		rprLightShape = cmds.createNode("RPRPhysicalLight", n="RPRPhysicalLightShape")
		rprLightShape = cmds.rename(rprLightShape, splited_name[-1] + "_rpr")
		rprTransform = cmds.listRelatives(rprLightShape, p=True)[0]
		rprTransform = cmds.rename(rprTransform, splited_name[-2] + "_rpr")
		rprLightShape = cmds.listRelatives(rprTransform)[0]

		if group:
			cmds.parent(rprTransform, group)

		rprTransform = group + "|" + rprTransform
		rprLightShape = rprTransform + "|" + rprLightShape
		
	# Logging to file 
	start_log(rs_light, rprLightShape)

	# Copy properties from rsLight
	copyProperty(rprTransform, rsTransform, "translateX", "translateX")
	copyProperty(rprTransform, rsTransform, "translateY", "translateY")
	copyProperty(rprTransform, rsTransform, "translateZ", "translateZ")
	copyProperty(rprTransform, rsTransform, "rotateX", "rotateX")
	copyProperty(rprTransform, rsTransform, "rotateY", "rotateY")
	copyProperty(rprTransform, rsTransform, "rotateZ", "rotateZ")
	copyProperty(rprTransform, rsTransform, "scaleX", "scaleX")
	copyProperty(rprTransform, rsTransform, "scaleY", "scaleY")
	copyProperty(rprTransform, rsTransform, "scaleZ", "scaleZ")

	lightType = getProperty(rs_light, "lightType")
	light_type_map = {
		0:0, # area
		1:2, # point
		2:1, # spot
		3:3  # directional
	}
	setProperty(rprLightShape, "lightType", light_type_map[lightType])
	
	areaShape = getProperty(rs_light, "areaShape")
	if lightType == 0: #area
		area_shape_map = {
			0:3,   # rectangle
			1:0,   # disc
			2:2,   # sphere
			3:1,   # cylinder
			4:4    # mesh 
		}
		setProperty(rprLightShape, "areaLightShape", area_shape_map[areaShape])

	intensity = getProperty(rs_light, "intensity")
	exposure = getProperty(rs_light, "exposure")
	unitsType = getProperty(rs_light, "unitsType")
	if unitsType == 0: #image 
		scale_multiplier = getProperty(rsTransform, "scaleX") * getProperty(rsTransform, "scaleY")
		if lightType == 0: #area #image -> lumen
			if areaShape in (0, 1): # rectangle or disk
				setProperty(rprLightShape, "intensityUnits", 0)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 2500 * scale_multiplier)
			elif areaShape == 2: # sphere
				setProperty(rprLightShape, "intensityUnits", 0)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 1000 * scale_multiplier)
			elif areaShape == 3: # cylinder
				copyProperty(rprTransform, rsTransform, "scaleX", "scaleZ")
				copyProperty(rprTransform, rsTransform, "scaleZ", "scaleX")
				setProperty(rprTransform, "rotateY", getProperty(rsTransform, "rotateY") + 90)
				setProperty(rprTransform, "rotateX", 0)
				scale_multiplier = getProperty(rsTransform, "scaleX") * getProperty(rsTransform, "scaleY")
				setProperty(rprLightShape, "intensityUnits", 0)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 335 * scale_multiplier)
			elif areaShape == 4: # mesh
				setProperty(rprLightShape, "intensityUnits", 0)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 1000 * scale_multiplier)
		elif lightType == 1: #point #image -> lumen
			setProperty(rprLightShape, "intensityUnits", 0)
			setProperty(rprLightShape, "lightIntensity", (intensity *  2 ** exposure) / (2500 * (1 + intensity *  2 ** exposure / 10000)))
		elif lightType == 2: #spot #image -> lumen
			setProperty(rprLightShape, "intensityUnits", 0)
			setProperty(rprLightShape, "lightIntensity", (intensity *  2 ** exposure) / (3000 * (1 + intensity *  2 ** exposure / 10000)))
		elif lightType == 3: # directional #image -> luminance
			setProperty(rprLightShape, "intensityUnits", 1)
			setProperty(rprLightShape, "lightIntensity", intensity * 3.3333)
	elif unitsType == 1: #luminous 
		if lightType == 0: #area 
			if areaShape in (0, 1, 2): # rectangle  disk sphere
				setProperty(rprLightShape, "intensityUnits", 0)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 30000)
			elif areaShape == 3: # cylinder
				copyProperty(rprTransform, rsTransform, "scaleX", "scaleZ")
				copyProperty(rprTransform, rsTransform, "scaleZ", "scaleX")
				setProperty(rprTransform, "rotateY", getProperty(rsTransform, "rotateY") + 90)
				setProperty(rprTransform, "rotateX", 0)
				setProperty(rprLightShape, "intensityUnits", 0)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 15000)
			elif areaShape == 4: # mesh
				setProperty(rprLightShape, "intensityUnits", 0)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 15000)
		elif lightType in (1, 2): #point and spot #luminous -> lumen
			setProperty(rprLightShape, "intensityUnits", 0)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 10000)
		elif lightType == 3: #directional  #luminous -> luminance
			setProperty(rprLightShape, "intensityUnits", 1)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure)
	elif unitsType == 2: #luminance -> luminance
		if lightType == 0: #area 
			if areaShape == 0: # rectangle  
				setProperty(rprLightShape, "intensityUnits", 1)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 6666.66)
			elif areaShape in (1, 2): # disk sphere
				setProperty(rprLightShape, "intensityUnits", 1)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 8333.33)
			elif areaShape == 3: # cylinder
				copyProperty(rprTransform, rsTransform, "scaleX", "scaleZ")
				copyProperty(rprTransform, rsTransform, "scaleZ", "scaleX")
				setProperty(rprTransform, "rotateY", getProperty(rsTransform, "rotateY") + 90)
				setProperty(rprTransform, "rotateX", 0)
				setProperty(rprLightShape, "intensityUnits", 1)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 5000)
			elif areaShape == 4: # mesh
				setProperty(rprLightShape, "intensityUnits", 1)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 5000)
		elif lightType == 1: #point #luminous -> lumen
			setProperty(rprLightShape, "intensityUnits", 0)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 30000000)
		elif lightType == 2: #spot #luminous -> lumen
			setProperty(rprLightShape, "intensityUnits", 0)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 10000)
		elif lightType == 3: #directional
			setProperty(rprLightShape, "intensityUnits", 1)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 3000)
	elif unitsType == 3: #radiant power -> watts
		if lightType == 0: #area 
			if areaShape in (0, 1, 2): # rectangle  disk sphere
				setProperty(rprLightShape, "intensityUnits", 2)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 45)
				copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
			elif areaShape == 3: # cylinder
				copyProperty(rprTransform, rsTransform, "scaleX", "scaleZ")
				copyProperty(rprTransform, rsTransform, "scaleZ", "scaleX")
				setProperty(rprTransform, "rotateY", getProperty(rsTransform, "rotateY") + 90)
				setProperty(rprTransform, "rotateX", 0)
				setProperty(rprLightShape, "intensityUnits", 2)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 20)
				copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
			elif areaShape == 4: # mesh
				setProperty(rprLightShape, "intensityUnits", 2)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 20)
				copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
		elif lightType in (1, 2): # point and spot #radiant power -> watts
			setProperty(rprLightShape, "intensityUnits", 2)
			setProperty(rprLightShape, "lightIntensity", (intensity *  2 ** exposure) / (15 * (0.92 + intensity *  2 ** exposure / 10000)))
			copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
		elif lightType == 3: #directional #radiant power -> luminance
			setProperty(rprLightShape, "intensityUnits", 1)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure * 20)
			copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
	elif unitsType == 4: #radiance - > radiance
		if lightType == 0: #area 
			if areaShape == 0: # rectangle
				setProperty(rprLightShape, "intensityUnits", 3)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 10)
				copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
			elif areaShape in (1, 2): # disk sphere
				setProperty(rprLightShape, "intensityUnits", 3)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 12.5)
				copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
			elif areaShape == 3: # cylinder
				copyProperty(rprTransform, rsTransform, "scaleX", "scaleZ")
				copyProperty(rprTransform, rsTransform, "scaleZ", "scaleX")
				setProperty(rprTransform, "rotateY", getProperty(rsTransform, "rotateY") + 90)
				setProperty(rprTransform, "rotateX", 0)
				setProperty(rprLightShape, "intensityUnits", 3)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 9)
				copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
			elif areaShape == 4: # mesh
				setProperty(rprLightShape, "intensityUnits", 3)
				setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 9)
				copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")
		elif lightType in (1, 2): #point and spot #radiance - > watts
			setProperty(rprLightShape, "intensityUnits", 2)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 44444.44444)
			copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")	
		elif lightType == 3: #directional #radiance - > radiance
			setProperty(rprLightShape, "intensityUnits", 3)
			setProperty(rprLightShape, "lightIntensity", intensity *  2 ** exposure / 5)
			copyProperty(rprLightShape, rs_light, "luminousEfficacy", "lumensperwatt")	

	if lightType == 0:
		copyProperty(rprLightShape, rs_light, "areaLightVisible", "areaVisibleInRender")
	elif lightType == 2:
		angle = getProperty(rs_light, "spotConeAngle")
		falloffAngle = getProperty(rs_light, "spotConeFalloffAngle")
		falloffCurve = getProperty(rs_light, "spotConeFalloffCurve")

		if falloffAngle*falloffCurve < falloffAngle*math.cos(falloffAngle):
			setProperty(rprLightShape, "spotLightOuterConeFalloff", angle + falloffAngle*falloffCurve)
			setProperty(rprLightShape, "spotLightInnerConeAngle", angle - falloffAngle*falloffCurve)
		elif falloffAngle*falloffCurve < 2*angle:
			outerConeFalloff = angle + falloffAngle*math.cos(falloffAngle)
			setProperty(rprLightShape, "spotLightOuterConeFalloff", outerConeFalloff)
			innerConeAngle = angle - falloffAngle*falloffCurve
			if innerConeAngle < 0:
				innerConeAngle = 0
			elif innerConeAngle > outerConeFalloff:
				innerConeAngle = outerConeFalloff
			setProperty(rprLightShape, "spotLightInnerConeAngle", innerConeAngle)
		else:
			outerConeFalloff = angle + falloffAngle*math.cos(falloffAngle)
			setProperty(rprLightShape, "spotLightOuterConeFalloff", outerConeFalloff)
			setProperty(rprLightShape, "spotLightInnerConeAngle", outerConeFalloff / 2)

	copyProperty(rprLightShape, rs_light, "colorPicker", "color")
	copyProperty(rprLightShape, rs_light, "temperature", "temperature")

	color_mode = getProperty(rs_light, "colorMode")
	if color_mode in (0, 2):
		setProperty(rprLightShape, "colorMode", 0)
	else:
		setProperty(rprLightShape, "colorMode", 1)
		mel.eval("onTemperatureChanged(\"{}\")".format(rprLightShape))

	# Logging to file
	end_log(rs_light)  


def convertRedshiftPortalLight(rs_light):

	# Redshift light transform
	splited_name = rs_light.split("|")
	rsTransform = "|".join(splited_name[0:-1])
	group = "|".join(splited_name[0:-2])

	if cmds.objExists(rsTransform + "_rpr"):
		rprTransform = rsTransform + "_rpr"
		rprLightShape = cmds.listRelatives(rprTransform)[0]
	else: 
		rprLightShape = cmds.createNode("RPRPhysicalLight", n="RPRPhysicalLightShape")
		rprLightShape = cmds.rename(rprLightShape, splited_name[-1] + "_rpr")
		rprTransform = cmds.listRelatives(rprLightShape, p=True)[0]
		rprTransform = cmds.rename(rprTransform, splited_name[-2] + "_rpr")
		rprLightShape = cmds.listRelatives(rprTransform)[0]

		if group:
			cmds.parent(rprTransform, group)

		rprTransform = group + "|" + rprTransform
		rprLightShape = rprTransform + "|" + rprLightShape

	# Logging to file 
	start_log(rs_light, rprLightShape)

	# Copy properties from rsLight

	setProperty(rprLightShape, "lightType", 0)

	intensity = getProperty(rs_light, "multiplier")
	exposure = getProperty(rs_light, "exposure")
	setProperty(rprLightShape, "lightIntensity", intensity * 2 ** exposure)
	setProperty(rprLightShape, "intensityUnits", 1)
	
	copyProperty(rprLightShape, rs_light, "colorPicker", "tint_color")

	visible = getProperty(rs_light, "transparency")
	if (visible[0] or visible[1] or visible[2]): 
		setProperty(rprLightShape, "areaLightVisible", 0)
	else:
		setProperty(rprLightShape, "areaLightVisible", 1)
	
	copyProperty(rprTransform, rsTransform, "translate", "translate")
	copyProperty(rprTransform, rsTransform, "rotate", "rotate")
	copyProperty(rprTransform, rsTransform, "scale", "scale")

	# Logging to file
	end_log(rs_light)  


def convertRedshiftIESLight(rs_light): 

	# Redshift light transform
	splited_name = rs_light.split("|")
	rsTransform = "|".join(splited_name[0:-1])
	group = "|".join(splited_name[0:-2])

	if cmds.objExists(rsTransform + "_rpr"):
		rprTransform = rsTransform + "_rpr"
		rprLightShape = cmds.listRelatives(rprTransform)[0]
	else: 
		rprLightShape = cmds.createNode("RPRIES", n="RPRIESLight")
		rprLightShape = cmds.rename(rprLightShape, splited_name[-1] + "_rpr")
		rprTransform = cmds.listRelatives(rprLightShape, p=True)[0]
		rprTransform = cmds.rename(rprTransform, splited_name[-2] + "_rpr")
		rprLightShape = cmds.listRelatives(rprTransform)[0]

		if group:
			cmds.parent(rprTransform, group)

		rprTransform = group + "|" + rprTransform
		rprLightShape = rprTransform + "|" + rprLightShape

	# Logging to file 
	start_log(rs_light, rprLightShape)

	# Copy properties from rsLight
	intensity = getProperty(rs_light, "multiplier")
	exposure = getProperty(rs_light, "exposure")
	setProperty(rprLightShape, "intensity", intensity * 2 ** exposure)
	copyProperty(rprLightShape, rs_light, "color", "color")
	setProperty(rprLightShape, "iesFile", getProperty(rs_light, "profile"))
	
	copyProperty(rprTransform, rsTransform, "translate", "translate")
	setProperty(rprTransform, "rotateX", getProperty(rsTransform, "rotateX") + 180)
	copyProperty(rprTransform, rsTransform, "rotateY", "rotateY")
	copyProperty(rprTransform, rsTransform, "rotateZ", "rotateZ")
	copyProperty(rprTransform, rsTransform, "scale", "scale")

	# Logging to file
	end_log(rs_light)  


def convertRedshiftVolumeScattering(rsVolumeScattering):

	# Creating new Volume material
	rprMaterial = cmds.shadingNode("RPRVolumeMaterial", asShader=True)
	rprMaterial = cmds.rename(rprMaterial, (rsVolumeScattering + "_rpr"))
	
	sg = rprMaterial + "SG"
	cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
	connectProperty(rprMaterial, "outColor", sg, "volumeShader")

	# create sphere
	cmds.polySphere(n="Volume")
	setProperty("Volume", "scale", (999, 999, 999))

	# assign material
	cmds.select("Volume")
	cmds.sets(e=True, forceElement=sg)

	# Logging to file 
	start_log(rsVolumeScattering, rprMaterial) 

	# Fields conversion
	copyProperty(rprMaterial, rsVolumeScattering, "scatterColor", "tint")
	copyProperty(rprMaterial, rsVolumeScattering, "scatteringDirection", "phase")
	copyProperty(rprMaterial, rsVolumeScattering, "emissionColor", "fogAmbient")

	density = getProperty(rsVolumeScattering, "scatteringAmount") * 8
	setProperty(rprMaterial, "density", density)
	
	# Logging to file
	end_log(rsVolumeScattering)  


# Convert material. Returns new material name.
def convertMaterial(rsMaterial, source):

	rs_type = cmds.objectType(rsMaterial)

	conversion_func = {
		"RedshiftArchitectural": convertRedshiftArchitectural,
		"RedshiftCarPaint": convertRedshiftCarPaint,
		"RedshiftHair": convertUnsupportedMaterial,
		"RedshiftIncandescent": convertRedshiftIncandescent,
		"RedshiftMaterial": convertRedshiftMaterial,
		"RedshiftMaterialBlender": convertRedshiftMaterialBlender,
		"RedshiftMatteShadowCatcher": convertRedshiftMatteShadowCatcher,
		"RedshiftShaderSwitch": convertUnsupportedMaterial,
		"RedshiftSkin": convertRedshiftSkin,
		"RedshiftSprite": convertRedshiftSprite,
		"RedshiftSubSurfaceScatter": convertRedshiftSubSurfaceScatter,
		##utilities
		"bump2d": convertbump2d,
		"multiplyDivide": convertmultiplyDivide,
		"RedshiftBumpMap": convertRedshiftBumpMap,
		"RedshiftNormalMap": convertRedshiftNormalMap,
		"RedshiftAmbientOcclusion": convertRedshiftAmbientOcclusion,
		"RedshiftFresnel": convertRedshiftFresnel,
		"RedshiftColorLayer": convertRedshiftColorLayer,
		"RedshiftBumpBlender": convertRedshiftBumpBlender,
		"RedshiftNoise": convertRedshiftNoise
		
	}

	if rs_type in conversion_func:
		rpr = conversion_func[rs_type](rsMaterial, source)
	else:
		if isRedshiftType(rsMaterial):
			rpr = convertUnsupportedNode(rsMaterial, source)
		else:
			rpr = convertStandartNode(rsMaterial, source)

	return rpr


# Convert light. Returns new light name.
def convertLight(light):

	rs_type = cmds.objectType(light)

	conversion_func = {
		"RedshiftPhysicalLight": convertRedshiftPhysicalLight,
		"RedshiftDomeLight": convertRedshiftDomeLight,
		"RedshiftPortalLight": convertRedshiftPortalLight,
		#"RedshiftPhysicalSun": convertRedshiftPhysicalSun,
		"RedshiftIESLight": convertRedshiftIESLight,
	}

	conversion_func[rs_type](light)


def isRedshiftType(obj):

	if cmds.objExists(obj):
		objType = cmds.objectType(obj)
		if "Redshift" in objType:
			return 1
	return 0


def cleanScene():

	listMaterials= cmds.ls(materials=True)
	for material in listMaterials:
		if isRedshiftType(material):
			shEng = cmds.listConnections(material, type="shadingEngine")
			try:
				cmds.delete(shEng[0])
				cmds.delete(material)
			except Exception as ex:
				traceback.print_exc()

	listLights = cmds.ls(l=True, type=["RedshiftDomeLight", "RedshiftIESLight", "RedshiftPhysicalLight", "RedshiftPhysicalSun", "RedshiftPortalLight"])
	for light in listLights:
		transform = cmds.listRelatives(light, p=True)
		try:
			cmds.delete(light)
			cmds.delete(transform[0])
		except Exception as ex:
			traceback.print_exc()

	listObjects = cmds.ls(l=True)
	for obj in listObjects:
		if isRedshiftType(object):
			try:
				cmds.delete(obj)
			except Exception as ex:
				traceback.print_exc()


def remap_value(value, maxInput, minInput, maxOutput, minOutput):

	value = maxInput if value > maxInput else value
	value = minInput if value < minInput else value

	inputDiff = maxInput - minInput
	outputDiff = maxOutput - minOutput

	remapped_value = minOutput + ((float(value - minInput) / float(inputDiff)) * outputDiff)

	return remapped_value


def clampValue(value, minValue, maxValue):
	return max(min(value, maxValue), minValue)


def checkAssign(material):

	if isRedshiftType(material):
		materialSG = cmds.listConnections(material, type="shadingEngine")
		if materialSG:
			cmds.hyperShade(objects=material)
			assigned = cmds.ls(sl=True)
			if assigned:
				return 1
	return 0


def defaultEnable(RPRmaterial, rsMaterial, enable, value):

	weight = getProperty(rsMaterial, value)
	if weight > 0:
		setProperty(RPRmaterial, enable, 1)
	else:
		setProperty(RPRmaterial, enable, 0)


def convertScene():

	# Check plugins
	if not cmds.pluginInfo("redshift4maya", q=True, loaded=True):
		cmds.loadPlugin("redshift4maya")

	if not cmds.pluginInfo("RadeonProRender", q=True, loaded=True):
		cmds.loadPlugin("RadeonProRender")

	# redshift engine set before conversion
	setProperty("defaultRenderGlobals","currentRenderer", "redshift")

	# Convert RedshiftEnvironment
	env = cmds.ls(type="RedshiftEnvironment")
	if env:
		try:
			convertRedshiftEnvironment(env[0])
		except Exception as ex:
			traceback.print_exc()
			print("Error while converting environment. ")

	# Convert RedshiftPhysicalSky
	sky = cmds.ls(type="RedshiftPhysicalSky")
	if sky:
		try:
			convertRedshiftPhysicalSky(sky[0])
		except Exception as ex:
			traceback.print_exc()
			print("Error while converting physical sky. \n")

	# Convert RedshiftAtmosphere
	atmosphere = cmds.ls(type="RedshiftVolumeScattering")
	if atmosphere:
		try:
			convertRedshiftVolumeScattering(atmosphere[0])
		except Exception as ex:
			traceback.print_exc()
			print("Error while converting volume scattering environment.")

	# Get all lights from scene
	listLights = cmds.ls(l=True, type=["RedshiftDomeLight", "RedshiftIESLight", "RedshiftPhysicalLight", "RedshiftPhysicalSun", "RedshiftPortalLight"])

	# Convert lights
	for light in listLights:
		try:
			convertLight(light)
		except Exception as ex:
			traceback.print_exc()
			print("Error while converting {} light. \n".format(light))
		

	# Get all materials from scene
	listMaterials = cmds.ls(materials=True)
	materialsDict = {}
	for each in listMaterials:
		if checkAssign(each):
			materialsDict[each] = convertMaterial(each, "")

	for rs, rpr in materialsDict.items():
		try:
			cmds.hyperShade(objects=rs)
			rpr_sg = cmds.listConnections(rpr, type="shadingEngine")[0]
			cmds.sets(forceElement=rpr_sg)
		except Exception as ex:
			traceback.print_exc()
			print("Error while converting {} material. \n".format(rs))
	
	# globals conversion
	try:
		setProperty("defaultRenderGlobals","currentRenderer", "FireRender")
		setProperty("defaultRenderGlobals", "imageFormat", 8)

		setProperty("RadeonProRenderGlobals", "completionCriteriaSeconds", 0)
		if getProperty("redshiftOptions", "progressiveRenderingEnabled"):
			setProperty("RadeonProRenderGlobals", "adaptiveThreshold", 0)
			setProperty("RadeonProRenderGlobals", "completionCriteriaIterations", getProperty("redshiftOptions", "progressiveRenderingNumPasses") * 1.5)
		else:
			copyProperty("RadeonProRenderGlobals", "redshiftOptions", "adaptiveThreshold", "unifiedAdaptiveErrorThreshold")
			if getProperty("redshiftOptions", "unifiedMinSamples") >= 16:
				copyProperty("RadeonProRenderGlobals", "redshiftOptions", "completionCriteriaMinIterations", "unifiedMinSamples")
			else:
				setProperty("RadeonProRenderGlobals", "completionCriteriaMinIterations", 16)
			copyProperty("RadeonProRenderGlobals", "redshiftOptions", "completionCriteriaIterations", "unifiedMaxSamples")

		setProperty("RadeonProRenderGlobals", "giClampIrradiance", 1)
		setProperty("RadeonProRenderGlobals", "giClampIrradianceValue", 5)

		rsSubSurfaceScatter = cmds.ls(type="RedshiftSubSurfaceScatter")
		if rsSubSurfaceScatter:
			setProperty("RadeonProRenderGlobals", "maxDepthDiffuse", 12)
			setProperty("RadeonProRenderGlobals", "maxRayDepth ", 12)

		copyProperty("RadeonProRenderGlobals", "redshiftOptions", "maxDepthGlossy", "reflectionMaxTraceDepth")
		copyProperty("RadeonProRenderGlobals", "redshiftOptions", "maxDepthRefraction", "refractionMaxTraceDepth")
		copyProperty("RadeonProRenderGlobals", "redshiftOptions", "maxRayDepth", "combinedMaxTraceDepth")
		copyProperty("RadeonProRenderGlobals", "redshiftOptions", "filter", "unifiedFilterType")
		copyProperty("RadeonProRenderGlobals", "redshiftOptions", "motionBlur", "motionBlurEnable")
		copyProperty("RadeonProRenderGlobals", "redshiftOptions", "motionBlurScale", "motionBlurFrameDuration")
	except:
		pass

	matteShadowCatcher = cmds.ls(materials=True, type="RedshiftMatteShadowCatcher")
	if matteShadowCatcher:
		try:
			setProperty("RadeonProRenderGlobals", "aovOpacity", 1)
			setProperty("RadeonProRenderGlobals", "aovBackground", 1)
			setProperty("RadeonProRenderGlobals", "aovShadowCatcher", 1)
		except Exception as ex:
			traceback.print_exc()

	rsPhotographicExposure = cmds.ls(type="RedshiftPhotographicExposure")
	if rsPhotographicExposure:
		if getProperty(rsPhotographicExposure[0], "enable"):
			setProperty("RadeonProRenderGlobals", "toneMappingType", 2)
			setProperty("RadeonProRenderGlobals", "toneMappingPhotolinearSensitivity", getProperty(rsPhotographicExposure[0], "filmSpeed") / 100.0)
			copyProperty("RadeonProRenderGlobals", rsPhotographicExposure[0], "toneMappingPhotolinearFstop", "fStop")

			reinhardFactor = getProperty(rsPhotographicExposure[0], "reinhardFactor")
			shutterRatio = getProperty(rsPhotographicExposure[0], "shutterRatio")
			if shutterRatio >= 800:
				exposure = (3.3 * (10 / (shutterRatio + 400) ** 0.5) / math.log((shutterRatio - 770) ** 0.7)) * 2 ** reinhardFactor
				setProperty("RadeonProRenderGlobals", "toneMappingPhotolinearExposure", exposure)
			elif shutterRatio < 800 and shutterRatio >= 43:
				exposure = (10 / math.log10(shutterRatio - 28) ** 3) * 2 ** reinhardFactor
				setProperty("RadeonProRenderGlobals", "toneMappingPhotolinearExposure", exposure)
			else:
				exposure = (10.5 / math.log10(shutterRatio + 1.25)) * 2 ** reinhardFactor
				setProperty("RadeonProRenderGlobals", "toneMappingPhotolinearExposure", exposure)

	rsBokeh = cmds.ls(type="RedshiftBokeh")
	if rsBokeh:
		if getProperty(rsBokeh[0], "dofOn"):
			dofUseBokehImage = getProperty(rsBokeh[0], "dofUseBokehImage")
			dofBokehNormalizationMode = getProperty(rsBokeh[0], "dofBokehNormalizationMode")
			if dofUseBokehImage == 0 or (dofUseBokehImage == 1 and dofBokehNormalizationMode != 0):
				setProperty("RadeonProRenderGlobals", "toneMappingPhotolinearExposure", getProperty("RadeonProRenderGlobals", "toneMappingPhotolinearExposure") / 2)
			elif dofUseBokehImage == 1 and dofBokehNormalizationMode == 0:
				setProperty("RadeonProRenderGlobals", "toneMappingPhotolinearExposure", getProperty("RadeonProRenderGlobals", "toneMappingPhotolinearExposure") / 10)


def auto_launch():
	convertScene()
	cleanScene()

def manual_launch():
	print("Convertion start!")
	startTime = 0
	testTime = 0
	startTime = time.time()
	convertScene()
	testTime = time.time() - startTime
	print("Convertion finished! Time: " + str(testTime))

	response = cmds.confirmDialog(title="Convertation finished",
							  message=("Total time: " + str(testTime) + "\nDelete all redshift instances?"),
							  button=["Yes", "No"],
							  defaultButton="Yes",
							  cancelButton="No",
							  dismissString="No")

	if response == "Yes":
		cleanScene()


def onMayaDroppedPythonFile(empty):
	manual_launch()

if __name__ == "__main__":
	manual_launch()



