"use client";

import {
    ChevronLeft,
    ChevronRight,
    ChevronsLeft,
    ChevronsRight,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

interface PaginationControlsProps {
    currentPage: number;
    totalItems: number;
    itemsPerPage: number;
    onPageChange: (page: number) => void;
    onLimitChange: (limit: number) => void;
    limitOptions?: number[];
    isLoading?: boolean;
}

export function PaginationControls({
    currentPage,
    totalItems,
    itemsPerPage,
    onPageChange,
    onLimitChange,
    limitOptions = [25, 50, 100, 200],
    isLoading = false,
}: PaginationControlsProps) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    const startItem = (currentPage - 1) * itemsPerPage + 1;
    const endItem = Math.min(currentPage * itemsPerPage, totalItems);

    const [jumpPage, setJumpPage] = useState("");

    // Sync jump input with current page
    useEffect(() => {
        setJumpPage("");
    }, [currentPage]);

    const handleJump = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
            const page = parseInt(jumpPage);
            if (page >= 1 && page <= totalPages) {
                onPageChange(page);
                setJumpPage("");
            }
        }
    };

    // Keyboard Navigation
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (isLoading) return;
            // Ignore if user is typing in an input/textarea
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

            switch (e.key) {
                case "ArrowLeft":
                    if (currentPage > 1) onPageChange(currentPage - 1);
                    break;
                case "ArrowRight":
                    if (currentPage < totalPages) onPageChange(currentPage + 1);
                    break;
                case "Home":
                    if (currentPage !== 1) onPageChange(1);
                    break;
                case "End":
                    if (currentPage !== totalPages) onPageChange(totalPages);
                    break;
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [currentPage, totalPages, isLoading, onPageChange]);

    // Generate page numbers to show
    const getPageNumbers = () => {
        const delta = 2;
        const range: (number | string)[] = [];

        for (let i = 1; i <= totalPages; i++) {
            if (
                i === 1 ||
                i === totalPages ||
                (i >= currentPage - delta && i <= currentPage + delta)
            ) {
                range.push(i);
            } else if (range[range.length - 1] !== "...") {
                range.push("...");
            }
        }
        return range;
    };

    if (totalItems === 0) return null;

    return (
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 py-4 border-t w-full">
            {/* Left: Showing Info & Limit */}
            <div className="flex items-center gap-4 text-sm text-gray-600">
                <span className="hidden sm:inline">
                    Showing <span className="font-medium text-foreground">{startItem}</span> to{" "}
                    <span className="font-medium text-foreground">{endItem}</span> of{" "}
                    <span className="font-medium text-foreground">{totalItems}</span> entries
                </span>
                <div className="flex items-center gap-2">
                    <span className="whitespace-nowrap">Show:</span>
                    <Select
                        value={itemsPerPage.toString()}
                        onValueChange={(v) => onLimitChange(Number(v))}
                    >
                        <SelectTrigger className="h-8 w-[70px]">
                            <SelectValue placeholder={itemsPerPage} />
                        </SelectTrigger>
                        <SelectContent side="top">
                            {limitOptions.map((limit) => (
                                <SelectItem key={limit} value={limit.toString()}>
                                    {limit}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* Center/Right: Pagination Buttons */}
            <div className="flex items-center gap-1 sm:gap-2">
                <div className="flex items-center gap-1">
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 hidden sm:flex"
                        onClick={() => onPageChange(1)}
                        disabled={currentPage === 1 || isLoading}
                        title="First page"
                    >
                        <ChevronsLeft className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onPageChange(currentPage - 1)}
                        disabled={currentPage === 1 || isLoading}
                        title="Previous page"
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                </div>

                <div className="flex items-center gap-1">
                    {getPageNumbers().map((page, idx) => (
                        typeof page === "number" ? (
                            <Button
                                key={idx}
                                variant={currentPage === page ? "default" : "outline"}
                                size="icon"
                                className={cn(
                                    "h-8 w-8",
                                    currentPage === page ? "bg-primary text-primary-foreground hover:bg-primary/90 cursor-default" : "hover:bg-muted"
                                )}
                                onClick={() => currentPage !== page && onPageChange(page)}
                                disabled={isLoading && currentPage !== page}
                            >
                                {page}
                            </Button>
                        ) : (
                            <span key={idx} className="px-1 text-gray-400 text-sm">...</span>
                        )
                    ))}
                </div>

                <div className="flex items-center gap-1">
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onPageChange(currentPage + 1)}
                        disabled={currentPage === totalPages || isLoading}
                        title="Next page"
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 hidden sm:flex"
                        onClick={() => onPageChange(totalPages)}
                        disabled={currentPage === totalPages || isLoading}
                        title="Last page"
                    >
                        <ChevronsRight className="h-4 w-4" />
                    </Button>
                </div>

                {/* Jump to Page */}
                <div className="flex items-center gap-2 ml-2 hidden sm:flex">
                    <span className="text-sm text-gray-500 whitespace-nowrap">Go to:</span>
                    <Input
                        type="number"
                        min={1}
                        max={totalPages}
                        className="h-8 w-[60px]"
                        placeholder={currentPage.toString()}
                        value={jumpPage}
                        onChange={(e) => setJumpPage(e.target.value)}
                        onKeyDown={handleJump}
                        disabled={isLoading}
                    />
                </div>
            </div>
        </div>
    );
}
