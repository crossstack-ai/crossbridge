package com.crossbridge.parser;

import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.expr.AnnotationExpr;
import com.github.javaparser.ast.expr.MemberValuePair;
import com.github.javaparser.ast.expr.NormalAnnotationExpr;
import com.github.javaparser.ast.expr.SingleMemberAnnotationExpr;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.*;

/**
 * AST-based parser for Java test files using JavaParser.
 * 
 * Extracts test metadata and outputs JSON for consumption by Python.
 */
public class JavaTestParser {

    private static final Gson gson = new GsonBuilder().setPrettyPrinting().create();

    public static void main(String[] args) {
        if (args.length == 0) {
            System.err.println("Usage: java -jar java-test-parser.jar <java-file>");
            System.exit(1);
        }

        String filePath = args[0];
        File file = new File(filePath);

        if (!file.exists()) {
            System.err.println("Error: File not found: " + filePath);
            System.exit(1);
        }

        try {
            TestClassMetadata metadata = parseTestFile(file);
            String json = gson.toJson(metadata);
            System.out.println(json);
        } catch (Exception e) {
            System.err.println("Error parsing file: " + e.getMessage());
            e.printStackTrace(System.err);
            System.exit(1);
        }
    }

    public static TestClassMetadata parseTestFile(File file) throws FileNotFoundException {
        CompilationUnit cu = StaticJavaParser.parse(file);

        TestClassMetadata metadata = new TestClassMetadata();

        // Extract package
        cu.getPackageDeclaration().ifPresent(pkg -> 
            metadata.packageName = pkg.getNameAsString()
        );

        // Extract imports
        cu.getImports().forEach(imp -> 
            metadata.imports.add(imp.getNameAsString())
        );

        // Find test class
        Optional<ClassOrInterfaceDeclaration> testClass = cu.findFirst(
            ClassOrInterfaceDeclaration.class,
            c -> c.isPublic() && !c.isInterface()
        );

        if (!testClass.isPresent()) {
            return metadata;
        }

        ClassOrInterfaceDeclaration classDecl = testClass.get();
        metadata.className = classDecl.getNameAsString();

        // Extract class-level annotations
        for (AnnotationExpr ann : classDecl.getAnnotations()) {
            metadata.annotations.add(parseAnnotation(ann));
        }

        // Extract test methods
        for (MethodDeclaration method : classDecl.getMethods()) {
            if (isTestMethod(method)) {
                TestMethodMetadata testMethod = parseTestMethod(method);
                metadata.testMethods.add(testMethod);
            }
        }

        return metadata;
    }

    private static boolean isTestMethod(MethodDeclaration method) {
        // Check for @Test annotation (JUnit or TestNG)
        return method.getAnnotations().stream()
            .anyMatch(ann -> ann.getNameAsString().equals("Test") ||
                           ann.getNameAsString().equals("ParameterizedTest") ||
                           ann.getNameAsString().equals("RepeatedTest"));
    }

    private static TestMethodMetadata parseTestMethod(MethodDeclaration method) {
        TestMethodMetadata testMethod = new TestMethodMetadata();
        testMethod.name = method.getNameAsString();
        
        // Line number
        method.getBegin().ifPresent(pos -> 
            testMethod.lineNumber = pos.line
        );

        // Annotations
        for (AnnotationExpr ann : method.getAnnotations()) {
            testMethod.annotations.add(parseAnnotation(ann));
        }

        return testMethod;
    }

    private static AnnotationMetadata parseAnnotation(AnnotationExpr ann) {
        AnnotationMetadata annotation = new AnnotationMetadata();
        annotation.name = ann.getNameAsString();

        // Extract annotation attributes
        if (ann instanceof SingleMemberAnnotationExpr) {
            SingleMemberAnnotationExpr singleAnn = (SingleMemberAnnotationExpr) ann;
            annotation.attributes.put("value", singleAnn.getMemberValue().toString());
        } else if (ann instanceof NormalAnnotationExpr) {
            NormalAnnotationExpr normalAnn = (NormalAnnotationExpr) ann;
            for (MemberValuePair pair : normalAnn.getPairs()) {
                annotation.attributes.put(
                    pair.getNameAsString(),
                    pair.getValue().toString()
                );
            }
        }

        return annotation;
    }

    // Data classes for JSON serialization

    static class TestClassMetadata {
        String packageName = "";
        String className = "";
        List<String> imports = new ArrayList<>();
        List<AnnotationMetadata> annotations = new ArrayList<>();
        List<TestMethodMetadata> testMethods = new ArrayList<>();
    }

    static class TestMethodMetadata {
        String name;
        Integer lineNumber;
        List<AnnotationMetadata> annotations = new ArrayList<>();
    }

    static class AnnotationMetadata {
        String name;
        Map<String, String> attributes = new HashMap<>();
    }
}
