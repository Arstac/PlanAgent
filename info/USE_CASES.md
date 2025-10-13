# Casos de Uso Extendidos - PlanAgent

## 🎯 ¿Qué Más Puede Hacer PlanAgent?

Actualmente el sistema está configurado para **generar artículos**, pero su arquitectura permite mucho más. El sistema puede hacer **cualquier tarea que se pueda descomponer en subtareas ejecutables**.

---

## 📚 Tabla de Contenidos

1. [Capacidades Actuales](#capacidades-actuales)
2. [Nuevos Casos de Uso](#nuevos-casos-de-uso)
3. [Cómo Añadir Nuevos Casos de Uso](#cómo-añadir-nuevos-casos-de-uso)
4. [Nuevos Arquetipos de Agentes](#nuevos-arquetipos-de-agentes)
5. [Nuevas Herramientas](#nuevas-herramientas)
6. [Ejemplos de Implementación](#ejemplos-de-implementación)

---

## Capacidades Actuales

### ✅ Generación de Artículos

**Flujo actual:**
```
Objetivo: "Escribir artículo sobre X"
    ↓
Plan:
  s1: ResearchAgent    → Investigar información
  s2: OutlineAgent     → Crear estructura
  s3: WriterAgent      → Redactar intro
  s4: WriterAgent      → Redactar cuerpo
  s5: WriterAgent      → Redactar conclusión
  s6: EditorAgent      → Revisar y mejorar
  s7: FactCheckerAgent → Verificar datos
    ↓
Output: Artículo completo en Markdown
```

**Herramientas usadas:**
- `web_search` - Buscar información
- `web_fetch` - Obtener contenido de URLs
- `llm_call` - Generar texto
- `write_artifact` - Guardar archivos
- `read_artifact` - Leer archivos
- `quality_check` - Verificar calidad
- `fact_verify` - Verificar hechos

---

## Nuevos Casos de Uso

### 🎓 1. Investigación Académica

**Objetivo:** "Investigar el estado del arte de X y crear un survey paper"

**Plan sugerido:**
```
s1: LiteratureSearchAgent
    → Buscar papers en arXiv, Google Scholar, Semantic Scholar
    → Herramientas: academic_search, web_search
    → Output: papers_list.json

s2: PaperAnalysisAgent (x5-10 en paralelo)
    → Analizar cada paper encontrado
    → Herramientas: web_fetch, pdf_extract, llm_call
    → Output: paper_X_analysis.json

s3: SynthesisAgent
    → Sintetizar hallazgos de todos los papers
    → Herramientas: read_artifact, llm_call
    → Output: synthesis.json

s4: SurveyWriterAgent
    → Escribir el survey paper completo
    → Herramientas: read_artifact, llm_call, write_artifact
    → Output: survey_paper.md

s5: CitationAgent
    → Generar bibliografía en formato BibTeX
    → Herramientas: read_artifact, citation_format
    → Output: references.bib
```

**Nuevas herramientas necesarias:**
- `academic_search` - Buscar en bases de datos académicas
- `pdf_extract` - Extraer texto de PDFs
- `citation_format` - Formatear citas (APA, MLA, Chicago, BibTeX)

---

### 💻 2. Desarrollo de Software

**Objetivo:** "Crear una aplicación web para gestión de tareas"

**Plan sugerido:**
```
s1: RequirementsAgent
    → Analizar y documentar requisitos
    → Herramientas: llm_call, write_artifact
    → Output: requirements.md

s2: ArchitectureAgent
    → Diseñar arquitectura del sistema
    → Herramientas: llm_call, diagram_generate
    → Output: architecture.md, diagrams/

s3: DatabaseSchemaAgent
    → Diseñar esquema de base de datos
    → Herramientas: llm_call, sql_validate
    → Output: schema.sql

s4: FrontendCodeAgent
    → Generar código del frontend (React)
    → Herramientas: code_generate, file_create
    → Output: frontend/

s5: BackendCodeAgent
    → Generar código del backend (FastAPI)
    → Herramientas: code_generate, file_create
    → Output: backend/

s6: TestGeneratorAgent
    → Generar tests unitarios e integración
    → Herramientas: code_generate, pytest_template
    → Output: tests/

s7: DockerAgent
    → Crear archivos Docker y docker-compose
    → Herramientas: template_render
    → Output: Dockerfile, docker-compose.yml

s8: DocumentationAgent
    → Generar documentación completa
    → Herramientas: read_artifact, markdown_generate
    → Output: README.md, docs/
```

**Nuevas herramientas necesarias:**
- `code_generate` - Generar código en diferentes lenguajes
- `file_create` - Crear archivos en el filesystem
- `diagram_generate` - Generar diagramas (Mermaid, PlantUML)
- `sql_validate` - Validar sintaxis SQL
- `template_render` - Renderizar templates

---

### 📊 3. Análisis de Datos

**Objetivo:** "Analizar dataset de ventas y crear dashboard interactivo"

**Plan sugerido:**
```
s1: DataLoaderAgent
    → Cargar y validar datos
    → Herramientas: csv_load, data_validate
    → Output: data.parquet

s2: DataCleaningAgent
    → Limpiar y transformar datos
    → Herramientas: pandas_transform, outlier_detect
    → Output: data_clean.parquet

s3: EDAAgent (Exploratory Data Analysis)
    → Análisis exploratorio
    → Herramientas: statistical_analysis, plot_generate
    → Output: eda_report.md, plots/

s4: FeatureEngineeringAgent
    → Crear features para ML
    → Herramientas: feature_transform, correlation_analysis
    → Output: features.parquet

s5: ModelTrainingAgent
    → Entrenar modelos predictivos
    → Herramientas: sklearn_train, model_evaluate
    → Output: model.pkl, metrics.json

s6: DashboardAgent
    → Crear dashboard interactivo
    → Herramientas: plotly_dashboard, streamlit_generate
    → Output: dashboard.py

s7: ReportAgent
    → Generar reporte ejecutivo
    → Herramientas: read_artifact, chart_embed, pdf_generate
    → Output: executive_report.pdf
```

**Nuevas herramientas necesarias:**
- `csv_load`, `parquet_load` - Cargar diferentes formatos
- `pandas_transform` - Operaciones con pandas
- `plot_generate` - Generar gráficos (matplotlib, plotly)
- `sklearn_train` - Entrenar modelos ML
- `streamlit_generate` - Generar apps Streamlit
- `pdf_generate` - Generar PDFs

---

### 🎨 4. Creación de Contenido Multimedia

**Objetivo:** "Crear un video educativo sobre X con guión, imágenes y narración"

**Plan sugerido:**
```
s1: ConceptAgent
    → Definir concepto y estructura del video
    → Herramientas: llm_call
    → Output: concept.json

s2: ScriptWriterAgent
    → Escribir guión con timestamps
    → Herramientas: llm_call, timestamp_calculate
    → Output: script.json

s3: ImageGeneratorAgent (x10)
    → Generar imágenes para cada escena
    → Herramientas: dalle_generate, midjourney_api
    → Output: images/scene_*.png

s4: VoiceoverAgent
    → Generar narración de audio
    → Herramientas: tts_generate (ElevenLabs, Google TTS)
    → Output: audio/narration.mp3

s5: BackgroundMusicAgent
    → Seleccionar/generar música de fondo
    → Herramientas: music_search, audio_generate
    → Output: audio/background.mp3

s6: VideoEditorAgent
    → Ensamblar video completo
    → Herramientas: ffmpeg_compose, subtitle_add
    → Output: final_video.mp4

s7: ThumbnailAgent
    → Generar thumbnail llamativo
    → Herramientas: image_generate, text_overlay
    → Output: thumbnail.png
```

**Nuevas herramientas necesarias:**
- `dalle_generate`, `midjourney_api` - Generar imágenes con IA
- `tts_generate` - Text-to-Speech
- `music_search` - Buscar música libre de derechos
- `ffmpeg_compose` - Editar video con FFmpeg
- `subtitle_add` - Añadir subtítulos

---

### 🛒 5. E-commerce y Marketing

**Objetivo:** "Lanzar producto nuevo con estrategia completa de marketing"

**Plan sugerido:**
```
s1: MarketResearchAgent
    → Investigar mercado y competencia
    → Herramientas: web_search, competitor_analysis
    → Output: market_research.json

s2: PersonaAgent
    → Crear buyer personas
    → Herramientas: llm_call, demographic_analysis
    → Output: personas.json

s3: ProductDescriptionAgent
    → Escribir descripciones de producto
    → Herramientas: llm_call, seo_optimize
    → Output: descriptions/

s4: AdCopyAgent
    → Crear copy para anuncios (Google, Facebook, Instagram)
    → Herramientas: llm_call, ad_preview
    → Output: ad_copies/

s5: EmailCampaignAgent
    → Crear secuencia de emails
    → Herramientas: llm_call, email_template
    → Output: email_sequence/

s6: SocialMediaAgent
    → Crear posts para redes sociales
    → Herramientas: llm_call, hashtag_suggest, image_generate
    → Output: social_posts/

s7: LandingPageAgent
    → Crear landing page HTML/CSS
    → Herramientas: code_generate, design_apply
    → Output: landing_page/

s8: AnalyticsDashboardAgent
    → Configurar tracking y dashboard
    → Herramientas: ga_setup, dashboard_create
    → Output: analytics_config.json
```

**Nuevas herramientas necesarias:**
- `competitor_analysis` - Analizar competidores
- `seo_optimize` - Optimizar para SEO
- `ad_preview` - Previsualizar anuncios
- `email_template` - Templates de email
- `hashtag_suggest` - Sugerir hashtags
- `ga_setup` - Configurar Google Analytics

---

### 🏥 6. Análisis Médico (con datos públicos)

**Objetivo:** "Analizar síntomas y crear reporte de posibles diagnósticos"

**⚠️ NOTA:** Solo para información educativa, no sustituye consulta médica.

**Plan sugerido:**
```
s1: SymptomAnalysisAgent
    → Analizar síntomas reportados
    → Herramientas: medical_database_search
    → Output: symptoms_analysis.json

s2: DifferentialDiagnosisAgent
    → Generar diagnósticos diferenciales
    → Herramientas: medical_knowledge_base, llm_call
    → Output: differential_diagnosis.json

s3: TestRecommendationAgent
    → Recomendar pruebas médicas
    → Herramientas: medical_guidelines
    → Output: recommended_tests.json

s4: ReportGeneratorAgent
    → Generar reporte para médico
    → Herramientas: medical_report_template
    → Output: medical_report.pdf

s5: PatientEducationAgent
    → Crear material educativo para paciente
    → Herramientas: llm_call, simplify_medical_terms
    → Output: patient_guide.md
```

---

### 🎓 7. Educación Personalizada

**Objetivo:** "Crear curso personalizado sobre X adaptado al nivel del estudiante"

**Plan sugerido:**
```
s1: AssessmentAgent
    → Evaluar nivel actual del estudiante
    → Herramientas: quiz_generate, answer_evaluate
    → Output: student_profile.json

s2: CurriculumAgent
    → Diseñar currículo personalizado
    → Herramientas: learning_path_generate
    → Output: curriculum.json

s3: ContentCreatorAgent (x10)
    → Crear lecciones individuales
    → Herramientas: llm_call, example_generate
    → Output: lessons/

s4: ExerciseGeneratorAgent
    → Crear ejercicios prácticos
    → Herramientas: problem_generate, solution_create
    → Output: exercises/

s5: QuizAgent
    → Crear quizzes de evaluación
    → Herramientas: quiz_generate, auto_grade
    → Output: quizzes/

s6: ProgressTrackerAgent
    → Crear sistema de seguimiento
    → Herramientas: dashboard_create
    → Output: progress_dashboard.html
```

---

### 🔬 8. Investigación Científica

**Objetivo:** "Diseñar y analizar experimento científico"

**Plan sugerido:**
```
s1: HypothesisAgent
    → Formular hipótesis basada en literatura
    → Herramientas: paper_search, hypothesis_formulate
    → Output: hypothesis.md

s2: ExperimentDesignAgent
    → Diseñar protocolo experimental
    → Herramientas: statistical_power_analysis
    → Output: experiment_protocol.md

s3: DataSimulationAgent
    → Simular datos esperados
    → Herramientas: monte_carlo_simulate
    → Output: simulated_data.csv

s4: StatisticalAnalysisAgent
    → Analizar datos (reales o simulados)
    → Herramientas: statistical_test, power_analysis
    → Output: statistical_report.md

s5: VisualizationAgent
    → Crear visualizaciones científicas
    → Herramientas: scientific_plot, figure_compose
    → Output: figures/

s6: PaperWriterAgent
    → Escribir paper científico
    → Herramientas: latex_generate, citation_format
    → Output: paper.tex, paper.pdf
```

---

### 🤖 9. Automatización de Procesos

**Objetivo:** "Automatizar proceso de onboarding de empleados"

**Plan sugerido:**
```
s1: ProcessMapAgent
    → Mapear proceso actual
    → Herramientas: bpmn_generate
    → Output: process_map.bpmn

s2: DocumentCollectorAgent
    → Recopilar documentos necesarios
    → Herramientas: file_list, template_collect
    → Output: documents_list.json

s3: WorkflowAgent
    → Crear workflow automatizado
    → Herramientas: zapier_create, n8n_workflow
    → Output: workflow.json

s4: EmailTemplateAgent
    → Crear templates de emails automáticos
    → Herramientas: email_template, variable_inject
    → Output: email_templates/

s5: ChecklistAgent
    → Crear checklists interactivos
    → Herramientas: checklist_generate
    → Output: checklists/

s6: DocumentationAgent
    → Documentar el proceso automatizado
    → Herramientas: doc_generate, video_tutorial
    → Output: process_documentation/
```

---

### 🎮 10. Desarrollo de Juegos

**Objetivo:** "Crear juego simple de texto/aventura"

**Plan sugerido:**
```
s1: GameDesignAgent
    → Diseñar mecánicas y narrativa
    → Herramientas: llm_call
    → Output: game_design.md

s2: StoryWriterAgent
    → Escribir historia y diálogos
    → Herramientas: llm_call, dialogue_tree
    → Output: story.json

s3: CharacterAgent
    → Crear personajes detallados
    → Herramientas: llm_call, character_sheet
    → Output: characters.json

s4: WorldBuildingAgent
    → Crear mundo del juego
    → Herramientas: location_generate, map_create
    → Output: world.json, map.png

s5: GameLogicAgent
    → Implementar lógica del juego
    → Herramientas: code_generate (Python/JavaScript)
    → Output: game_logic.py

s6: UIAgent
    → Crear interfaz de usuario
    → Herramientas: html_generate, css_generate
    → Output: ui/

s7: TestAgent
    → Crear tests y playtest
    → Herramientas: game_test, bug_detect
    → Output: test_report.md
```

---

## Cómo Añadir Nuevos Casos de Uso

### Paso 1: Identificar los Arquetipos Necesarios

Para cada caso de uso, necesitas identificar qué tipos de agentes especializados necesitas.

**Ejemplo: Caso de Uso "Análisis de Datos"**

```python
# En planner.py, añadir al system prompt:

**DataLoaderAgent**: Carga y valida datos
- Tools: csv_load, data_validate, write_artifact
- Genera: data.parquet con datos validados
- Acceptance: schema con {"rows": number, "columns": list}
- System prompt con PASOS:
  1. Cargar dataset con csv_load
  2. Validar con data_validate
  3. OBLIGATORIO: write_artifact con data.parquet
  4. Responder JSON step_result

**DataCleaningAgent**: Limpia y transforma datos
- Tools: read_artifact, pandas_transform, write_artifact
- Lee: data.parquet del DataLoaderAgent
- Genera: data_clean.parquet
- Acceptance: text_checks con min_rows
```

### Paso 2: Crear las Herramientas Necesarias

```python
# En src/plan_spawn/core/tools/data_tools.py

@register_tool(
    name="csv_load",
    description="Cargar archivo CSV y convertir a Parquet",
    parameters={
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Ruta al archivo CSV"
            },
            "delimiter": {
                "type": "string",
                "description": "Delimitador (por defecto ',')",
                "default": ","
            }
        },
        "required": ["filepath"]
    }
)
async def csv_load(
    filepath: str,
    delimiter: str = ",",
    step_id: str = None,
    artifact_store = None,
    **kwargs
) -> Dict[str, Any]:
    """Cargar CSV y guardar como Parquet."""
    try:
        import pandas as pd

        # Cargar CSV
        df = pd.read_csv(filepath, delimiter=delimiter)

        # Convertir a Parquet
        parquet_path = f"/tmp/{step_id}_data.parquet"
        df.to_parquet(parquet_path)

        # Guardar en artifact store
        with open(parquet_path, 'rb') as f:
            content = f.read()

        uri = artifact_store.save(
            step_id=step_id,
            name="data.parquet",
            content=content,
            content_type="parquet"
        )

        return {
            "status": "success",
            "uri": uri,
            "rows": len(df),
            "columns": df.columns.tolist()
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@register_tool(
    name="pandas_transform",
    description="Aplicar transformaciones pandas a un dataset",
    parameters={
        "type": "object",
        "properties": {
            "data_uri": {
                "type": "string",
                "description": "URI del artifact con los datos"
            },
            "operations": {
                "type": "array",
                "description": "Lista de operaciones a aplicar",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["drop_na", "fill_na", "drop_duplicates", "rename_columns"]
                        },
                        "params": {"type": "object"}
                    }
                }
            }
        },
        "required": ["data_uri", "operations"]
    }
)
async def pandas_transform(
    data_uri: str,
    operations: List[Dict],
    step_id: str = None,
    artifact_store = None,
    **kwargs
) -> Dict[str, Any]:
    """Aplicar transformaciones a datos."""
    try:
        import pandas as pd

        # Cargar datos
        content = artifact_store.load(data_uri)
        df = pd.read_parquet(content)

        # Aplicar operaciones
        for op in operations:
            if op["type"] == "drop_na":
                df = df.dropna(**op.get("params", {}))
            elif op["type"] == "fill_na":
                df = df.fillna(**op["params"])
            elif op["type"] == "drop_duplicates":
                df = df.drop_duplicates(**op.get("params", {}))
            # ... más operaciones

        # Guardar resultado
        output_path = f"/tmp/{step_id}_clean.parquet"
        df.to_parquet(output_path)

        with open(output_path, 'rb') as f:
            uri = artifact_store.save(
                step_id=step_id,
                name="data_clean.parquet",
                content=f.read()
            )

        return {
            "status": "success",
            "uri": uri,
            "rows": len(df),
            "operations_applied": len(operations)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### Paso 3: Añadir Modo CLI

```python
# En main.py

async def run_data_analysis_mode(dataset_path: str):
    """Modo de análisis de datos."""
    console.print("\n[bold]Data Analysis Mode[/bold]\n")

    objective = f"Analizar dataset en {dataset_path} y crear reporte completo con insights"

    # Inicializar orchestrator
    orchestrator = Orchestrator()

    # Ejecutar
    state = await orchestrator.run(
        objective,
        context={"dataset_path": dataset_path}
    )

    if state.status == "completed":
        console.print("\n[bold green]✓ Análisis completado![/bold green]\n")
        # Mostrar artifacts generados


# En main()
elif command == "analyze":
    if len(sys.argv) > 2:
        dataset_path = sys.argv[2]
        await run_data_analysis_mode(dataset_path)
```

**Uso:**
```bash
python -m plan_spawn.main analyze data/sales.csv
```

---

## Nuevos Arquetipos de Agentes

### Template para Nuevos Arquetipos

```python
**[NombreAgente]**: [Descripción breve]
- Tools: [lista de tools]
- Lee: [artifacts de entrada]
- Genera: [artifacts de salida]
- Acceptance: [tipo de validación]
- System prompt con PASOS:
  1. [Paso 1]
  2. [Paso 2]
  3. OBLIGATORIO: write_artifact con [nombre_archivo]
  4. Responder INMEDIATAMENTE con JSON step_result (NO MÁS TOOLS)
- Enfatizar: "Después de write_artifact, DETENTE y devuelve JSON"
```

### Ejemplos de Arquetipos por Dominio

#### Desarrollo de Software
- **CodeReviewAgent** - Revisar código y sugerir mejoras
- **RefactorAgent** - Refactorizar código existente
- **TestGeneratorAgent** - Generar tests automáticamente
- **DocumentationAgent** - Generar documentación de código
- **SecurityAuditAgent** - Auditar seguridad del código

#### Data Science
- **DataProfilerAgent** - Perfilar datasets
- **FeatureEngineerAgent** - Crear features para ML
- **ModelTrainerAgent** - Entrenar modelos ML
- **HyperparameterTunerAgent** - Optimizar hiperparámetros
- **ModelExplainerAgent** - Explicar predicciones (SHAP, LIME)

#### Marketing
- **SEOOptimizerAgent** - Optimizar contenido para SEO
- **AdCopyWriterAgent** - Escribir copy publicitario
- **SocialMediaAgent** - Crear posts para RRSS
- **EmailMarketingAgent** - Crear campañas de email
- **CompetitorAnalysisAgent** - Analizar competencia

#### Diseño
- **UIDesignerAgent** - Diseñar interfaces de usuario
- **BrandingAgent** - Crear identidad de marca
- **InfographicAgent** - Crear infografías
- **PrototypeAgent** - Crear prototipos interactivos

---

## Nuevas Herramientas

### Categorías de Herramientas a Añadir

#### 1. Código y Desarrollo
```python
- code_generate       # Generar código en múltiples lenguajes
- code_review         # Revisar código automáticamente
- git_operations      # Operaciones git (commit, push, PR)
- package_install     # Instalar dependencias
- lint_check          # Linting (pylint, eslint)
- format_code         # Formatear código (black, prettier)
- run_tests           # Ejecutar tests
- build_project       # Build del proyecto
- deploy_service      # Deploy a cloud (Vercel, Heroku, AWS)
```

#### 2. Datos y Análisis
```python
- sql_query           # Ejecutar queries SQL
- dataframe_transform # Operaciones pandas/polars
- statistical_test    # Tests estadísticos
- ml_train            # Entrenar modelos ML
- ml_predict          # Hacer predicciones
- plot_generate       # Generar gráficos
- dashboard_create    # Crear dashboards (Streamlit, Dash)
```

#### 3. Multimedia
```python
- image_generate      # Generar imágenes (DALL-E, Midjourney)
- image_edit          # Editar imágenes (crop, resize, filter)
- video_create        # Crear videos (FFmpeg)
- audio_generate      # Generar audio (TTS, music)
- audio_transcribe    # Transcribir audio (Whisper)
- subtitle_generate   # Generar subtítulos
```

#### 4. Web y APIs
```python
- api_call            # Llamar APIs REST
- graphql_query       # Queries GraphQL
- web_scrape          # Scraping avanzado
- browser_automate    # Automatización con Playwright
- form_submit         # Enviar formularios
- auth_login          # Login automatizado
```

#### 5. Documentos
```python
- pdf_generate        # Crear PDFs
- pdf_extract         # Extraer texto/imágenes de PDF
- docx_create         # Crear Word docs
- excel_create        # Crear Excel
- latex_compile       # Compilar LaTeX
- markdown_to_html    # Convertir Markdown
```

#### 6. Cloud y DevOps
```python
- aws_s3_upload       # Subir a S3
- aws_lambda_deploy   # Deploy Lambda
- docker_build        # Build imagen Docker
- kubernetes_deploy   # Deploy a K8s
- cloudflare_deploy   # Deploy a Cloudflare
```

---

## Ejemplos de Implementación

### Ejemplo 1: Sistema de Generación de Informes Empresariales

```bash
# Comando
python -m plan_spawn.main business-report Q4-2024

# Plan generado automáticamente
s1: DataCollectorAgent
    → Recopilar datos de ventas, marketing, finanzas
    → write_artifact: raw_data.json

s2: DataAnalysisAgent
    → Analizar KPIs y tendencias
    → write_artifact: analysis.json

s3: ChartGeneratorAgent
    → Crear visualizaciones
    → write_artifact: charts/

s4: InsightsAgent
    → Extraer insights clave
    → write_artifact: insights.md

s5: ReportWriterAgent
    → Escribir reporte ejecutivo
    → write_artifact: executive_report.md

s6: PDFGeneratorAgent
    → Generar PDF final con branding
    → write_artifact: Q4_Report.pdf

# Output
./artifacts/s6/Q4_Report.pdf
```

### Ejemplo 2: Automatización de Reclutamiento

```bash
# Comando
python -m plan_spawn.main recruit "Senior Python Developer"

# Plan
s1: JobDescriptionAgent
    → Crear descripción de puesto optimizada
    → write_artifact: job_description.md

s2: InterviewQuestionsAgent
    → Generar preguntas técnicas
    → write_artifact: interview_questions.json

s3: CodingChallengeAgent
    → Crear desafío de código
    → write_artifact: coding_challenge/

s4: ScoringRubricAgent
    → Crear rúbrica de evaluación
    → write_artifact: scoring_rubric.json

s5: EmailTemplateAgent
    → Crear templates de emails
    → write_artifact: email_templates/

# Output
Complete recruitment package ready!
```

### Ejemplo 3: Creador de Cursos Online

```bash
# Comando
python -m plan_spawn.main course "Introduction to Python"

# Plan
s1: CurriculumAgent → curriculum.json
s2: LessonCreatorAgent (x12) → lessons/
s3: ExerciseGeneratorAgent → exercises/
s4: QuizAgent → quizzes/
s5: VideoScriptAgent → scripts/
s6: PresentationAgent → slides/
s7: PackagerAgent → course_package.zip

# Output
./artifacts/s7/python_course_package.zip
```

---

## Limitaciones y Consideraciones

### ⚠️ Limitaciones Actuales

1. **No ejecuta código arbitrario** - Por seguridad, no ejecuta código sin restricciones
2. **Sin acceso a sistemas externos** - No puede modificar bases de datos reales sin tools específicas
3. **Dependiente de tools** - Solo puede hacer lo que las tools permiten
4. **Sin GUI** - Todo es via CLI actualmente
5. **Sin memoria persistente** - Cada ejecución es independiente

### 🔐 Consideraciones de Seguridad

Al añadir nuevas capacidades, considera:

- **Sandboxing** - Ejecutar código en contenedores aislados
- **Rate limiting** - Limitar llamadas a APIs externas
- **Validación de inputs** - Sanitizar todos los inputs
- **Permisos** - Control granular de qué puede hacer cada agente
- **Logging** - Auditar todas las acciones
- **Secrets management** - No hardcodear API keys

---

## Roadmap de Expansión

### Fase 1: Fundamentos (✅ Completado)
- [x] Sistema de artículos funcional
- [x] Planner robusto
- [x] Herramientas básicas
- [x] Gestión de artifacts

### Fase 2: Expansión de Capacidades
- [ ] Añadir 5 arquetipos de Data Science
- [ ] Añadir 5 arquetipos de Desarrollo
- [ ] 20+ nuevas herramientas
- [ ] Modo interactivo mejorado

### Fase 3: Especialización
- [ ] Paquetes de arquetipos por industria
- [ ] Templates de planes comunes
- [ ] Marketplace de tools custom
- [ ] Plugins system

### Fase 4: Escala y Performance
- [ ] Ejecución paralela de steps
- [ ] Distributed execution
- [ ] Caching inteligente
- [ ] Optimización de costos

### Fase 5: Experiencia de Usuario
- [ ] Web UI dashboard
- [ ] VS Code extension
- [ ] Slack/Discord bot
- [ ] API REST

---

## Conclusión

**PlanAgent es un framework universal para tareas decomponibles.**

La clave es:
1. **Identificar arquetipos** necesarios para tu dominio
2. **Crear tools** específicas
3. **Definir planes** que usen esos arquetipos
4. **Iterar y mejorar** basado en resultados

**El límite es tu imaginación** y las tools que implementes.

---

## Recursos

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Arquitectura del sistema
- [FLOW_DIAGRAMS.md](./FLOW_DIAGRAMS.md) - Diagramas de flujo
- [Anthropic Tool Use Docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)

---

**¿Ideas? ¡Comparte tus casos de uso!**
