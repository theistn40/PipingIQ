from knowledge_library.knowledge_library import KnowledgeLibrary

library = KnowledgeLibrary("knowledge_library/source_documents")

library.scan_library()

library.print_library()