#---------------------------------------------------------------------------
# Name:        etgtools/sip_generator.py
# Author:      Robin Dunn
#
# Created:     3-Nov-2010
# Copyright:   (c) 2011 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

"""
The generator class for creating SIP definition files from the data
objects produced by the ETG scripts.
"""

import sys, os, re
import extractors
import generators
from cStringIO import StringIO


divider = '//' + '-'*75 + '\n'
phoenixRoot = os.path.abspath(os.path.split(__file__)[0]+'/..')

# This is a list of types that are used as return by value or by reference
# function return types that we need to ensure are actually using pointer
# types in their CppMethodDef or cppCode wrappers.
forcePtrTypes = [ 'wxString', 
                  ]

#---------------------------------------------------------------------------

class SipWrapperGenerator(generators.WrapperGeneratorBase):
        
    def generate(self, module, destFile=None):
        stream = StringIO()
        
        # generate SIP code from the module and its objects
        self.generateModule(module, stream)
        
        # Write the contents of the stream to the destination file
        if not destFile:
            destFile = os.path.join(phoenixRoot, 'sip/gen', module.name + '.sip')
        file(destFile, 'wt').write(stream.getvalue())
            
        
    #-----------------------------------------------------------------------
    def generateModule(self, module, stream):
        assert isinstance(module, extractors.ModuleDef)

        # write the file header
        stream.write(divider + """\
// This file is generated by wxPython's SIP generator.  Do not edit by hand.
// 
// Copyright: (c) 2011 by Total Control Software
// License:   wxWindows License
""")
        if module.name == module.module:
            stream.write("""
%%Module( name=%s.%s, 
         keyword_arguments="All",
         use_argument_names=True, 
         language="C++")
{
    %%AutoPyName(remove_leading="wx")
};

%%Copying
    Copyright: (c) 2011 by Total Control Software
    License:   wxWindows License
%%End

""" % (module.package, module.name))

            if module.name.startswith('_'):
                doc = ''
                if module.docstring:
                    doc = '\n"""\n%s\n"""\n' % module.docstring 
                stream.write("""\
%%Extract(id=pycode%s, order=5)
# This file is generated by wxPython's SIP generator.  Do not edit by hand.
# 
# Copyright: (c) 2011 by Total Control Software
# License:   wxWindows License
%s
from %s import *

%%End

""" % ( module.name, doc, module.name))
            
        else:
            stream.write("//\n// This file will be included by %s.sip\n//\n" % module.module)
        
        stream.write(divider)

        self.module_name = module.module
        # C++ code to be written to the module's header 
        if module.headerCode:
            stream.write("\n%ModuleHeaderCode\n")
            for c in module.headerCode:
                stream.write('%s\n' % c)
            stream.write("%End\n\n")
                
        # %Imports and %Includes
        if module.imports:
            for i in module.imports:
                stream.write("%%Import %s.sip\n" % i)
            stream.write("\n")
        if module.includes:
            for i in module.includes:
                stream.write("%%Include %s.sip\n" % i)
            stream.write("\n")
        
        # C++ code to be written out to the generated module
        if module.cppCode:
            stream.write("%ModuleCode\n")
            for c in module.cppCode:
                stream.write('%s\n' % c)
            stream.write("%End\n")

        stream.write('\n%s\n' % divider)
            
        # Now generate each of the items in the module
        self.generateModuleItems(module, stream)
                    
        # Add code for the module initialization sections.
        if module.preInitializerCode:
            stream.write('\n%s\n\n%%PreInitialisationCode\n' % divider)
            for i in module.preInitializerCode:
                stream.write('%s\n' % i)
            stream.write('%End\n')            
        if module.initializerCode:
            stream.write('\n%s\n\n%%InitialisationCode\n' % divider)
            for i in module.initializerCode:
                stream.write('%s\n' % i)
            stream.write('%End\n')            
        if module.postInitializerCode:
            stream.write('\n%s\n\n%%PostInitialisationCode\n' % divider)
            for i in module.postInitializerCode:
                stream.write('%s\n' % i)
            stream.write('%End\n')            
            
        stream.write('\n%s\n' % divider)
        
        
        
    def generateModuleItems(self, module, stream):
        methodMap = {
            extractors.ClassDef         : self.generateClass,
            extractors.DefineDef        : self.generateDefine,
            extractors.FunctionDef      : self.generateFunction,
            extractors.EnumDef          : self.generateEnum,
            extractors.GlobalVarDef     : self.generateGlobalVar,
            extractors.TypedefDef       : self.generateTypedef,
            extractors.WigCode          : self.generateWigCode,
            extractors.PyCodeDef        : self.generatePyCode,
            extractors.CppMethodDef     : self.generateCppMethod,
            extractors.CppMethodDef_sip : self.generateCppMethod_sip,
            }
        
        for item in module:
            if item.ignored:
                continue
            function = methodMap[item.__class__]
            function(item, stream)
        
        
    #-----------------------------------------------------------------------
    def generateFunction(self, function, stream, _needDocstring=True):
        assert isinstance(function, extractors.FunctionDef)
        if not function.ignored:
            stream.write('%s %s(' % (function.type, function.name))
            if function.items:
                stream.write('\n')
                self.generateParameters(function.items, stream, ' '*4)
            stream.write(')%s;\n' % self.annotate(function))

            if  _needDocstring:
                self.generateDocstring(function, stream, '')
                # We only write a docstring for the first overload, otherwise
                # SIP appends them all together.
                _needDocstring = False

            if function.cppCode:
                code, codeType = function.cppCode
                if codeType == 'sip':
                    stream.write('%MethodCode\n')
                    stream.write(nci(code, 4))
                    stream.write('%End\n')
                elif codeType == 'function':
                    raise NotImplementedError() # TODO: See generateMethod for an example, refactor to share code...
        for f in function.overloads:
            self.generateFunction(f, stream, _needDocstring)
        stream.write('\n')            

        
    def generateParameters(self, parameters, stream, indent):
        for idx, param in enumerate(parameters):
            if param.ignored:
                continue
            stream.write(indent)
            stream.write('%s %s' % (param.type, param.name))
            stream.write(self.annotate(param))
            if param.default:
                stream.write(' = %s' % param.default)
            if not idx == len(parameters)-1:
                stream.write(',')
            stream.write('\n')
        
        
    #-----------------------------------------------------------------------
    def generateEnum(self, enum, stream, indent=''):
        assert isinstance(enum, extractors.EnumDef)
        if enum.ignored:
            return
        name = enum.name
        if name.startswith('@'):
            name = ''
        stream.write('%senum %s%s\n%s{\n' % (indent, name, self.annotate(enum), indent))
        values = []
        for v in enum.items:
            if v.ignored:
                continue
            values.append("%s    %s%s" % (indent, v.name, self.annotate(v)))
        stream.write(',\n'.join(values))
        stream.write('%s\n%s};\n\n' % (indent, indent))
        
        
    #-----------------------------------------------------------------------
    def generateGlobalVar(self, globalVar, stream):
        assert isinstance(globalVar, extractors.GlobalVarDef)
        if globalVar.ignored:
            return

        stream.write('%s %s' % (globalVar.type, globalVar.name))
        stream.write('%s;\n\n' % self.annotate(globalVar))
        

    #-----------------------------------------------------------------------
    def generateDefine(self, define, stream):
        assert isinstance(define, extractors.DefineDef)
        if define.ignored:
            return
        # We're assuming that the #define is an integer value, tell sip that it is
        #stream.write('enum { %s };\n' % define.name)
        stream.write('const int %s;\n' % define.name)
        
        
    #-----------------------------------------------------------------------
    def generateTypedef(self, typedef, stream):
        assert isinstance(typedef, extractors.TypedefDef)
        if typedef.ignored:
            return
        stream.write('typedef %s %s' % (typedef.type, typedef.name))
        stream.write('%s;\n\n' % self.annotate(typedef))
        
        
    #-----------------------------------------------------------------------
    def generateWigCode(self, wig, stream, indent=''):
        assert isinstance(wig, extractors.WigCode)
        stream.write(nci(wig.code, len(indent), False))
        stream.write('\n\n')
    
    
    #-----------------------------------------------------------------------
    def generatePyCode(self, pc, stream, indent=''):
        assert isinstance(pc, extractors.PyCodeDef)
        if hasattr(pc, 'klass') and pc.klass.generatingInClass:
            pc.klass.generateAfterClass.append(pc)
        else:
            stream.write('%%Extract(id=pycode%s' % self.module_name)
            if pc.order is not None:
                stream.write(', order=%d' % pc.order)
            stream.write(')\n')
            stream.write(nci(pc.code))
            stream.write('\n%End\n\n')
    
    
    #-----------------------------------------------------------------------
    def generateClass(self, klass, stream, indent=''):
        assert isinstance(klass, extractors.ClassDef)
        if klass.ignored:
            return
        
        # write the class header
        stream.write('%s%s %s' % (indent, klass.kind, klass.name))
        if klass.bases:
            stream.write(' : ')
            stream.write(', '.join(klass.bases))
        stream.write(self.annotate(klass))
        stream.write('\n%s{\n' % indent)
        indent2 = indent + ' '*4

        if klass.briefDoc is not None:
            self.generateDocstring(klass, stream, indent2)

        if klass.includes:
            stream.write('%s%%TypeHeaderCode\n' % indent2)
            for inc in klass.includes:
                stream.write('%s    #include <%s>\n' % (indent2, inc))
            stream.write('%s%%End\n\n' % indent2)

        # C++ code to be written to the Type's header 
        if klass.headerCode:
            stream.write("%s%%TypeHeaderCode\n" % indent2)
            for c in klass.headerCode:
                stream.write(nci(c, len(indent2)+4))
            stream.write("%s%%End\n" % indent2)
                
        # C++ code to be written out to the this Type's wrapper code module
        if klass.cppCode:
            stream.write("%s%%TypeCode\n" % indent2)
            for c in klass.cppCode:
                stream.write(nci(c, len(indent2)+4))
            stream.write("%s%%End\n" % indent2)
            
        if klass.kind == 'class':
            stream.write('\n%spublic:\n' % indent)

        # is the generator currently inside the class or after it?
        klass.generatingInClass = True 
        
        # Split the items into public and protected groups
        ctors = [i for i in klass if 
                    isinstance(i, extractors.MethodDef) and 
                    i.protection == 'public' and (i.isCtor or i.isDtor)]
        public = [i for i in klass if i.protection == 'public' and i not in ctors]
        protected = [i for i in klass if i.protection == 'protected']
        
        dispatch = {
            extractors.MemberVarDef     : self.generateMemberVar,
            extractors.PropertyDef      : self.generateProperty,
            extractors.MethodDef        : self.generateMethod,
            extractors.EnumDef          : self.generateEnum,
            extractors.CppMethodDef     : self.generateCppMethod,
            extractors.CppMethodDef_sip : self.generateCppMethod_sip,
            extractors.PyMethodDef      : self.generatePyMethod,
            extractors.PyCodeDef        : self.generatePyCode,
            extractors.WigCode          : self.generateWigCode,
            # TODO: nested classes too?
            }
        for item in ctors:
            f = dispatch[item.__class__]
            f(item, stream, indent + ' '*4)
            
        for item in public:
            item.klass = klass
            f = dispatch[item.__class__]
            f(item, stream, indent + ' '*4)

        if protected and [i for i in protected if not i.ignored]:
            stream.write('\nprotected:\n')
            for item in protected:
                f = dispatch[item.__class__]
                f(item, stream, indent + ' '*4)

        if klass.convertFromPyObject:
            self.generateConvertCode('%ConvertToTypeCode',
                                     klass.convertFromPyObject,
                                     stream, indent + ' '*4)

        if klass.convertToPyObject:
            self.generateConvertCode('%ConvertFromTypeCode',
                                     klass.convertToPyObject,
                                     stream, indent + ' '*4)
            
        stream.write('%s};  // end of class %s\n\n\n' % (indent, klass.name))
        
        # Now generate anything that was deferred until after the class is finished
        klass.generatingInClass = False
        for item in klass.generateAfterClass:
            f = dispatch[item.__class__]
            f(item, stream, indent)
            
        

    def generateConvertCode(self, kind, code, stream, indent):
        stream.write('%s%s\n' % (indent, kind))
        stream.write(nci(code, len(indent)+4))
        stream.write('%s%%End\n' % indent)
        
            
    def generateMemberVar(self, memberVar, stream, indent):
        assert isinstance(memberVar, extractors.MemberVarDef)
        if memberVar.ignored:
            return
        stream.write('%s%s %s' % (indent, memberVar.type, memberVar.name))
        stream.write('%s;\n\n' % self.annotate(memberVar))

        
    def generateProperty(self, prop, stream, indent):
        assert isinstance(prop, extractors.PropertyDef)
        if prop.ignored:
            return
        stream.write('%s%%Property(name=%s, get=%s' % (indent, prop.name, prop.getter))
        if prop.setter:
            stream.write(', set=%s' % prop.setter)
        stream.write(')')
        if prop.briefDoc:
            stream.write(' // %s' % prop.briefDoc)
        stream.write('\n')
        
        
    def generateDocstring(self, item, stream, indent):
        # get the docstring text
        text = extractors.flattenNode(item.briefDoc)
        
        if isinstance(item, extractors.ClassDef):
            # append the function signatures for the class constructors (if any) to the class' docstring
            try:
                ctor = item.find(item.name)
                sigs = ctor.collectPySignatures()
                if sigs:
                    text += '\n\n' + '\n'.join(sigs)
            except extractors.ExtractorError:
                pass
        else:
            # Prepend function signature string(s) for functions and methods
            sigs = item.collectPySignatures()                
            if sigs:
                if text:
                    text = '\n\n' + text
                text = '\n'.join(sigs) + text
                
        # write the directive and the text
        if True:
            # SIP is preserving all leading whitespace in the docstring, so
            # write this without indents. :-(
            stream.write('%%Docstring\n%s\n%%End\n' % text)
        else:
            stream.write('%s%%Docstring\n' % indent)
            stream.write(nci(text, len(indent)+4))
            stream.write('%s%%End\n' % indent)
            
        
    def generateMethod(self, method, stream, indent, _needDocstring=True):
        assert isinstance(method, extractors.MethodDef)
        if not method.ignored:
            if method.isVirtual:
                stream.write("%svirtual\n" % indent)
            if method.isStatic:
                stream.write("%sstatic\n" % indent)
            if method.isCtor or method.isDtor:
                stream.write('%s%s(' % (indent, method.name))
            else:
                stream.write('%s%s %s(' % (indent, method.type, method.name))
            if method.items:
                stream.write('\n')
                self.generateParameters(method.items, stream, indent+' '*4)
                stream.write(indent)
            stream.write(')')
            if method.isConst:
                stream.write(' const')
            if method.isPureVirtual:
                stream.write(' = 0')
            stream.write('%s;\n' % self.annotate(method))
                        
            if  _needDocstring and not (method.isCtor or method.isDtor):
                self.generateDocstring(method, stream, indent)
                # We only write a docstring for the first overload, otherwise
                # SIP appends them all together.
                _needDocstring = False
                
            if method.cppCode:
                code, codeType = method.cppCode
                if codeType == 'sip':
                    stream.write('%s%%MethodCode\n' % indent)
                    stream.write(nci(code, len(indent)+4))
                    stream.write('%s%%End\n' % indent)
                elif codeType == 'function':
                    cm = extractors.CppMethodDef.FromMethod(method)
                    cm.body = code
                    self.generateCppMethod(cm, stream, indent, skipDeclaration=True)
                
            stream.write('\n')
        if method.overloads:
            for m in method.overloads:
                self.generateMethod(m, stream, indent, _needDocstring)

            
    def generateCppMethod(self, method, stream, indent='', skipDeclaration=False):
        # Add a new C++ method to a class. This one adds the code as a
        # separate function and then adds a call to that function in the
        # MethodCode directive.
        assert isinstance(method, extractors.CppMethodDef)
        if method.ignored:
            return
        
        lastP = method.argsString.rfind(')')
        pnames = method.argsString[:lastP].strip('()').split(',')
        for idx, pn in enumerate(pnames):
            # take only the part before the =, if there is one
            name = pn.split('=')[0].strip()   
            # now get just the part after and space, * or &, which should be
            # the parameter name
            name = re.split(r'[ \*\&]+', name)[-1] 
            pnames[idx] = name
        pnames = ', '.join(pnames)
        if pnames:
            pnames = ', ' + pnames
        typ = method.type
        argsString = method.argsString

        if not skipDeclaration:
            # First insert the method declaration
            if method.isCtor:
                stream.write('%s%s%s%s;\n' % 
                             (indent, method.name, argsString, self.annotate(method)))
            else:
                constMod = ""
                if method.isConst:
                    constMod = " const"
                stream.write('%s%s %s%s%s%s;\n' % 
                             (indent, typ, method.name, argsString, constMod, self.annotate(method)))
    
            # write the docstring
            self.generateDocstring(method, stream, indent)
                
        klass = method.klass
        if klass:
            assert isinstance(klass, extractors.ClassDef)

        # create the new function
        fstream = StringIO()  # using a new stream so we can do the actual write a little later
        lastP = method.argsString.rfind(')')
        fargs = method.argsString[:lastP].strip('()').split(',')
        for idx, arg in enumerate(fargs):
            # take only the part before the =, if there is one
            arg = arg.split('=')[0].strip()   
            arg = arg.replace('&', '*')  # SIP will always want to use pointers for parameters
            fargs[idx] = arg
        fargs = ', '.join(fargs)
        if fargs:
            fargs = ', ' + fargs
        if method.isCtor:
            fname = '_%s_newCtor' % klass.name
            fargs = '(int& _isErr%s)' % fargs
            fstream.write('%s%%TypeCode\n' % indent)
            typ = klass.name
            if method.useDerivedName:
                typ = 'sip'+klass.name
                fstream.write('%sclass %s;\n' % (indent, typ))   # forward decalre the derived class
            fstream.write('%s%s* %s%s\n%s{\n' % (indent, typ, fname, fargs, indent))
            fstream.write(nci(method.body, len(indent)+4))
            fstream.write('%s}\n' % indent)
            fstream.write('%s%%End\n' % indent)
            
        else:
            if klass:
                fname = '_%s_%s' % (klass.name, method.name)
                if method.isStatic:
                    # If the method is static then there is no sipCpp to send to
                    # the new function, so it should not have a self parameter.
                    fargs = '(int& _isErr%s)' % fargs
                else:
                    fargs = '(%s* self, int& _isErr%s)' % (klass.name, fargs)
                fstream.write('%s%%TypeCode\n' % indent)
            else:
                fname = '_%s_function' % method.name
                fargs = '(int& _isErr%s)' % fargs
                fstream.write('%s%%ModuleCode\n' % indent)
            
            # If the return type is in the forcePtrTypes list then make sure
            # that it is a pointer, not a return by value or reference, since
            # SIP almost always deals with pointers to newly allocated
            # objects.
            typPtr = method.type
            if typPtr in forcePtrTypes:
                if '&' in typPtr:
                    typPtr.replace('&', '*')
                elif '*' not in typPtr:
                    typPtr += '*'
        
            fstream.write('%s%s %s%s\n%s{\n' % (indent, typPtr, fname, fargs, indent))
            fstream.write(nci(method.body, len(indent)+4))
            fstream.write('%s}\n' % indent)
            fstream.write('%s%%End\n' % indent)

        # Write the code that will call the new function
        stream.write('%s%%MethodCode\n' % indent)
        stream.write(indent+' '*4)
        if method.isCtor:
            stream.write('sipCpp = %s(sipIsErr%s);\n' % (fname, pnames))
        else:
            if method.type != 'void':
                stream.write('sipRes = ')
            if klass:
                if method.isStatic:
                    # If the method is static then there is no sipCpp to send to
                    # the new function, so it should not have a self parameter.
                    stream.write('%s(sipIsErr%s);\n' % (fname, pnames))
                else:
                    stream.write('%s(sipCpp, sipIsErr%s);\n' % (fname, pnames))
            else:
                stream.write('%s(sipIsErr%s);\n' % (fname, pnames))
        stream.write('%s%%End\n' % indent)

        # and finally, add the new function itself
        stream.write(fstream.getvalue())
        stream.write('\n')
        

        
    def generateCppMethod_sip(self, method, stream, indent=''):
        # Add a new C++ method to a class without the extra generated
        # function, so SIP specific stuff can be done in the function body.
        assert isinstance(method, extractors.CppMethodDef_sip)
        if method.ignored:
            return
        if method.isCtor:
            stream.write('%s%s%s%s;\n' % 
                         (indent, method.name, method.argsString, self.annotate(method)))
        else:
            stream.write('%s%s %s%s%s;\n' % 
                         (indent, method.type, method.name, method.argsString, 
                          self.annotate(method)))
        stream.write('%s%%MethodCode\n' % indent)
        stream.write(nci(method.body, len(indent)+4))
        stream.write('%s%%End\n\n' % indent)
        # TODO: add the %Docstring...

        
        
    def generatePyMethod(self, pm, stream, indent):
        assert isinstance(pm, extractors.PyMethodDef)
        if pm.klass.generatingInClass:
            pm.klass.generateAfterClass.append(pm)
        else:
            klassName = pm.klass.pyName or pm.klass.name
            stream.write("%%Extract(id=pycode%s)\n" % self.module_name)
            stream.write("def _%s_%s%s:\n" % (klassName, pm.name, pm.argsString))
            if pm.briefDoc:
                stream.write(nci('"""\n%s\n"""\n' % pm.briefDoc, 4))
            stream.write(nci(pm.body, 4))
            if pm.deprecated:
                stream.write('%s.%s = wx.deprecated(_%s_%s)\n' % (klassName, pm.name, klassName, pm.name))
            else:
                stream.write('%s.%s = _%s_%s\n' % (klassName, pm.name, klassName, pm.name))
            stream.write('del _%s_%s\n' % (klassName, pm.name))
            stream.write('\n%End\n\n')

    #-----------------------------------------------------------------------

    def annotate(self, item):
        annotations = []
        if item.pyName:
            if not getattr(item, 'wxDropped', False):
                annotations.append('PyName=%s' % item.pyName)

        if isinstance(item, extractors.ParamDef):
            if item.out:
                annotations.append('Out')
            if item.inOut:
                annotations.extend(['In', 'Out'])
            if item.array:
                annotations.append('Array')
            if item.arraySize:
                annotations.append('ArraySize')
            if item.keepReference:
                annotations.append('KeepReference')
                
        if isinstance(item, (extractors.ParamDef, extractors.FunctionDef)):
            if item.transfer:
                annotations.append('Transfer')
            if item.transferBack:
                annotations.append('TransferBack')
            if item.transferThis:
                annotations.append('TransferThis')
            if item.pyInt:
                annotations.append('PyInt')
                
        if isinstance(item, extractors.VariableDef):
            if item.pyInt:
                annotations.append('PyInt')

        if isinstance(item, extractors.FunctionDef):
            if item.deprecated:
                annotations.append('Deprecated')
            if item.factory:
                annotations.append('Factory')
            if item.pyReleaseGIL:   # else HoldGIL??
                annotations.append('ReleaseGIL')
            if item.noCopy:
                annotations.append('NoCopy')
            
        if isinstance(item, extractors.MethodDef):
            if item.defaultCtor:
                annotations.append('Default')
            if item.noDerivedCtor:
                annotations.append('NoDerived')
            
        if isinstance(item, extractors.ClassDef):
            if item.abstract:
                annotations.append('Abstract')
            if item.allowNone:
                annotations.append('AllowNone')
            if item.deprecated:
                annotations.append('Deprecated')
            if item.external:
                annotations.append('External')
            if item.noDefCtor:
                annotations.append('NoDefaultCtors')
            if item.singlton:
                annotations.append('DelayDtor')
        
        if annotations:
            return '   /%s/' % ', '.join(annotations)
        else:
            return ''

#---------------------------------------------------------------------------
# helpers and utilities

def nci(text, numSpaces=0, stripLeading=True):
    """
    Normalize Code Indents
    
    First use the count of leading spaces on the first line and remove that
    many spaces from the front of all lines, and then indent each line by
    adding numSpaces spaces. This is used so we can convert the arbitrary
    indents that might be used by the tweaker code into what is expected for
    the context we are generating for.
    """
    def _getLeadingSpaceCount(line):
        count = 0
        for c in line:
            assert c != '\t', "Use spaces for indent, not tabs"
            if c != ' ':
                break
            count += 1
        return count
    
    def _allSpaces(text):
        for c in text:
            if c != ' ':
                return False
        return True

    
    lines = text.rstrip().split('\n')
    if stripLeading:
        numStrip = _getLeadingSpaceCount(lines[0])
    else:
        numStrip = 0
    
    for idx, line in enumerate(lines):
        assert _allSpaces(line[:numStrip]), "Indentation inconsistent with first line"
        lines[idx] = ' '*numSpaces + line[numStrip:]

    newText = '\n'.join(lines) + '\n'
    return newText


class SipGeneratorError(RuntimeError):
    pass


#---------------------------------------------------------------------------
